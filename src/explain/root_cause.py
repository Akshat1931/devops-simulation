from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import List, Dict, Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder
from lightgbm import LGBMClassifier
import shap

from src.utils.data_prep import label_before_after


@dataclass
class SegmentShift:
    key: str
    metric: str
    before: float
    after: float
    delta: float


@dataclass
class RootCauseReport:
    change_time: dt.datetime
    latency_before: float
    latency_after: float
    error_before: float
    error_after: float
    top_segments: List[SegmentShift]
    shap_importance: List[Dict[str, Any]]


def _segment_stats(
    df: pd.DataFrame,
    by_cols: List[str],
) -> List[SegmentShift]:
    segments: List[SegmentShift] = []
    group = df.groupby(by_cols)
    for key, frame in group:
        if frame["period"].nunique() < 2:
            continue
        before = frame[frame["period"] == "before"]
        after = frame[frame["period"] == "after"]
        if before.empty or after.empty:
            continue

        def _err_rate(f: pd.DataFrame) -> float:
            return (f["status_code"] >= 500).mean()

        lat_before = before["latency_ms"].mean()
        lat_after = after["latency_ms"].mean()
        err_before = _err_rate(before)
        err_after = _err_rate(after)

        name = (
            key
            if isinstance(key, str)
            else ", ".join(f"{c}={v}" for c, v in zip(by_cols, key, strict=False))
        )

        segments.append(
            SegmentShift(
                key=name,
                metric="avg_latency_ms",
                before=float(lat_before),
                after=float(lat_after),
                delta=float(lat_after - lat_before),
            )
        )

        segments.append(
            SegmentShift(
                key=name,
                metric="error_rate",
                before=float(err_before),
                after=float(err_after),
                delta=float(err_after - err_before),
            )
        )

    # sort by absolute delta, keep top few
    segments.sort(key=lambda s: abs(s.delta), reverse=True)
    return segments[:10]


def _train_shap_model(window_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Train a simple classifier to distinguish BEFORE vs AFTER
    and return SHAP feature importances.
    """
    feature_cols = ["latency_ms"]
    cat_cols = ["region", "device", "endpoint"]

    X_num = window_df[feature_cols].to_numpy()
    ohe = OneHotEncoder(sparse_output=False)
    X_cat = ohe.fit_transform(window_df[cat_cols])

    X = np.hstack([X_num, X_cat])
    y = (window_df["period"] == "after").astype(int).to_numpy()

    model = LGBMClassifier(
        n_estimators=80,
        max_depth=-1,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    model.fit(X, y)

    explainer = shap.TreeExplainer(model)
    # Newer versions of SHAP return a single ndarray for binary classification,
    # older versions return a list of arrays (one per class).
    shap_raw = explainer.shap_values(X)
    if isinstance(shap_raw, list):
        shap_values = shap_raw[1]  # class "after"
    else:
        shap_values = shap_raw

    # shap_values has shape (n_samples, n_features)
    mean_abs = np.abs(shap_values).mean(axis=0)

    feature_names = feature_cols + list(ohe.get_feature_names_out(cat_cols))
    importance = []
    for idx, name in enumerate(feature_names):
        # Guard against any length mismatch just in case
        if idx >= len(mean_abs):
            break
        importance.append({"feature": name, "importance": float(mean_abs[idx])})
    importance.sort(key=lambda d: d["importance"], reverse=True)
    return importance[:10]


def build_root_cause_report(
    events: pd.DataFrame,
    change_time: dt.datetime,
    window_minutes: int = 60,
) -> RootCauseReport:
    """
    Generate a compact root-cause report for a detected change time.
    """
    window_df = label_before_after(
        events=events, change_time=change_time, window_minutes=window_minutes
    )
    if window_df.empty:
        raise ValueError("No data in before/after window around change time.")

    before = window_df[window_df["period"] == "before"]
    after = window_df[window_df["period"] == "after"]

    def _err_rate(f: pd.DataFrame) -> float:
        return (f["status_code"] >= 500).mean()

    lat_before = before["latency_ms"].mean()
    lat_after = after["latency_ms"].mean()
    err_before = _err_rate(before)
    err_after = _err_rate(after)

    segments = []
    segments.extend(_segment_stats(window_df, ["endpoint"]))
    segments.extend(_segment_stats(window_df, ["region"]))
    segments.extend(_segment_stats(window_df, ["device"]))
    segments.extend(_segment_stats(window_df, ["endpoint", "region", "device"]))

    # deduplicate by (key, metric)
    dedup: Dict[tuple, SegmentShift] = {}
    for s in segments:
        k = (s.key, s.metric)
        if k not in dedup:
            dedup[k] = s
    segments = list(dedup.values())
    segments.sort(key=lambda s: abs(s.delta), reverse=True)
    segments = segments[:12]

    # To keep runtime manageable, subsample for SHAP
    if len(window_df) > 5000:
        window_df = window_df.sample(5000, random_state=42)

    shap_importance = _train_shap_model(window_df)

    return RootCauseReport(
        change_time=change_time,
        latency_before=float(lat_before),
        latency_after=float(lat_after),
        error_before=float(err_before),
        error_after=float(err_after),
        top_segments=segments,
        shap_importance=shap_importance,
    )

