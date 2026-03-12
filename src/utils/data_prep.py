import datetime as dt
from dataclasses import dataclass
from typing import Tuple, List, Optional

import numpy as np
import pandas as pd


@dataclass
class SyntheticEventConfig:
    days: int = 7
    base_requests_per_minute: int = 40
    seed: int = 42
    latency_mean_ms: float = 180.0
    latency_std_ms: float = 40.0
    error_rate: float = 0.015


REGIONS = ["US-East", "US-West", "EU-West", "IN-South"]
DEVICES = ["android", "ios", "web"]
ENDPOINTS = ["/login", "/search", "/checkout", "/feed"]


def generate_synthetic_events(
    config: SyntheticEventConfig | None = None,
) -> Tuple[pd.DataFrame, dt.datetime]:
    """
    Generate synthetic request-level logs with a hidden incident:
    a latency + error spike for android + IN-South + /login starting at a change time.
    """
    if config is None:
        config = SyntheticEventConfig()

    rng = np.random.default_rng(config.seed)

    start = dt.datetime.now().replace(second=0, microsecond=0) - dt.timedelta(
        days=config.days
    )
    minutes = config.days * 24 * 60
    timestamps = [start + dt.timedelta(minutes=i) for i in range(minutes)]

    # Hidden event starts halfway through the period
    change_idx = minutes // 2 + minutes // 6
    change_time = timestamps[change_idx]

    records: List[dict] = []
    for i, ts in enumerate(timestamps):
        # Poisson number of requests that minute
        n_requests = rng.poisson(config.base_requests_per_minute)
        if n_requests == 0:
            continue

        regions = rng.choice(REGIONS, size=n_requests)
        devices = rng.choice(DEVICES, size=n_requests)
        endpoints = rng.choice(ENDPOINTS, size=n_requests, p=[0.25, 0.4, 0.15, 0.2])

        # Baseline latency and errors
        base_latency = rng.normal(
            loc=config.latency_mean_ms, scale=config.latency_std_ms, size=n_requests
        )
        base_latency = np.clip(base_latency, 20, None)
        error_flags = rng.random(size=n_requests) < config.error_rate

        # Inject hidden event after change_time for specific segment
        if ts >= change_time:
            mask_segment = (
                (regions == "IN-South")
                & (devices == "android")
                & (endpoints == "/login")
            )
            base_latency[mask_segment] += 80.0
            # Double error rate for that segment
            extra_errors = rng.random(size=n_requests) < (
                config.error_rate * 1.5
            )
            error_flags = error_flags | (extra_errors & mask_segment)

        status_codes = np.where(error_flags, 500, 200)

        for r, d, e, lat, sc in zip(
            regions, devices, endpoints, base_latency, status_codes, strict=False
        ):
            records.append(
                {
                    "timestamp": ts,
                    "latency_ms": float(lat),
                    "status_code": int(sc),
                    "region": r,
                    "device": d,
                    "endpoint": e,
                }
            )

    events = pd.DataFrame.from_records(records)
    events.sort_values("timestamp", inplace=True)
    events.reset_index(drop=True, inplace=True)

    return events, change_time


def aggregate_windows(
    events: pd.DataFrame,
    freq: str = "5min",
) -> pd.DataFrame:
    """
    Aggregate request-level events into time windows with metrics.
    """
    df = events.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)

    def _agg_frame(frame: pd.DataFrame) -> pd.Series:
        if frame.empty:
            return pd.Series(
                {
                    "avg_latency_ms": np.nan,
                    "p95_latency_ms": np.nan,
                    "error_rate": np.nan,
                    "requests": 0,
                }
            )
        errors = frame["status_code"] >= 500
        return pd.Series(
            {
                "avg_latency_ms": frame["latency_ms"].mean(),
                "p95_latency_ms": frame["latency_ms"].quantile(0.95),
                "error_rate": errors.mean(),
                "requests": len(frame),
            }
        )

    agg = df.groupby(pd.Grouper(freq=freq)).apply(_agg_frame)
    agg.index.name = "timestamp"
    agg.reset_index(inplace=True)
    return agg


def label_before_after(
    events: pd.DataFrame,
    change_time: dt.datetime,
    window_minutes: int = 60,
) -> pd.DataFrame:
    """
    Label rows as BEFORE vs AFTER around a detected change time.
    """
    df = events.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    before_start = change_time - dt.timedelta(minutes=window_minutes)
    after_end = change_time + dt.timedelta(minutes=window_minutes)

    mask = (df["timestamp"] >= before_start) & (df["timestamp"] <= after_end)
    window_df = df.loc[mask].copy()
    window_df["period"] = np.where(
        window_df["timestamp"] < change_time, "before", "after"
    )
    return window_df

