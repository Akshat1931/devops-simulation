from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd
import ruptures as rpt


@dataclass
class ChangePointResult:
    change_times: List[pd.Timestamp]
    drift_score: pd.Series


def detect_changepoints(
    series: pd.Series,
    n_bkps: int = 3,
    model: str = "l2",
) -> List[int]:
    """
    Use ruptures to detect a few strong change points on a univariate series.
    Returns indices (integer positions) in the series.
    """
    y = series.astype(float).to_numpy()
    algo = rpt.Pelt(model=model).fit(y)
    # 'pen' controls number of breakpoints; tune lightly for demo
    bkps = algo.predict(pen=np.std(y) * 2.0)
    # ruptures returns segment end indices; drop final point
    indices = sorted(set(bkps[:-1]))
    return indices


def compute_drift_score(
    series: pd.Series,
    window: int = 12,
) -> pd.Series:
    """
    Simple drift score: absolute difference between rolling means
    of the left and right windows around each point.
    """
    y = series.astype(float)
    left = y.rolling(window=window, min_periods=1).mean()
    right = y.iloc[::-1].rolling(window=window, min_periods=1).mean().iloc[::-1]
    score = (right - left).abs()
    score.name = "drift_score"
    return score


def find_change_times(
    windows: pd.DataFrame,
    metric_col: str = "avg_latency_ms",
    time_col: str = "timestamp",
    max_points: int = 3,
) -> ChangePointResult:
    """
    High-level helper:
    - runs change-point detection on a chosen metric
    - computes a drift score series
    - returns a small list of candidate change times
    """
    df = windows.dropna(subset=[metric_col]).reset_index(drop=True)
    if df.empty:
        return ChangePointResult(change_times=[], drift_score=pd.Series(dtype=float))

    indices = detect_changepoints(df[metric_col])
    if len(indices) > max_points:
        # keep the ones with highest drift score
        drift = compute_drift_score(df[metric_col])
        ranked = sorted(indices, key=lambda i: drift.iloc[i], reverse=True)
        indices = ranked[:max_points]

    times = [pd.to_datetime(df.loc[i, time_col]) for i in indices]
    drift_score = compute_drift_score(df.set_index(time_col)[metric_col])
    return ChangePointResult(change_times=times, drift_score=drift_score)

