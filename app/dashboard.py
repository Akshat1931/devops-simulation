import os
import sys
import datetime as dt

import altair as alt
import pandas as pd
import streamlit as st

# Ensure project root (which contains `src/`) is on the import path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils.data_prep import (
    SyntheticEventConfig,
    generate_synthetic_events,
    aggregate_windows,
)
from src.detect.change_point import find_change_times
from src.explain.root_cause import build_root_cause_report
from src.explain.gemini_client import explain_incident


@st.cache_data(show_spinner=False)
def _generate_data(
    seed: int,
    days: int,
    base_rpm: int,
    freq: str,
):
    cfg = SyntheticEventConfig(
        days=days,
        base_requests_per_minute=base_rpm,
        seed=seed,
    )
    events, true_change_time = generate_synthetic_events(cfg)
    windows = aggregate_windows(events, freq=freq)
    return events, windows, true_change_time


def _format_ts(ts: dt.datetime | pd.Timestamp) -> str:
    if isinstance(ts, pd.Timestamp):
        ts = ts.to_pydatetime()
    return ts.strftime("%Y-%m-%d %H:%M")


def main() -> None:
    st.set_page_config(
        page_title="Neural Time Machine",
        page_icon="⏱️",
        layout="wide",
    )

    # Simple cache for Gemini explanations keyed by change_time
    if "gemini_cache" not in st.session_state:
        st.session_state["gemini_cache"] = {}

    st.title("Neural Time Machine")
    st.caption(
        "It takes time-based data, finds **when reality changed**, and explains **what caused it**."
    )

    with st.sidebar:
        st.header("Data source")
        data_mode = st.radio(
            "Choose data",
            ["Use synthetic demo data", "Upload my own CSV"],
            index=0,
        )

        uploaded_file = None
        if data_mode == "Upload my own CSV":
            uploaded_file = st.file_uploader(
                "Upload CSV with columns: timestamp, latency_ms, status_code, region, device, endpoint",
                type=["csv"],
            )

        st.markdown("---")
        st.header("Simulation controls (synthetic)")
        seed = st.slider("Random seed", 1, 9999, 42, help="Regenerate a new universe.")
        days = st.selectbox("Days of history", [3, 7, 14], index=1)
        base_rpm = st.slider(
            "Base requests / minute", 10, 150, 40, step=5, help="Traffic volume."
        )
        freq = st.selectbox(
            "Aggregation window", ["1min", "5min", "15min"], index=1
        )
        metric = st.selectbox(
            "Detection metric",
            ["avg_latency_ms", "p95_latency_ms", "error_rate"],
            index=0,
        )

        st.markdown("---")
        has_gemini = bool(os.getenv("GEMINI_API_KEY"))
        st.markdown(
            f"**Gemini status**: {'✅ Configured' if has_gemini else '⚠️ Not configured'}"
        )
        if not has_gemini:
            st.caption(
                "Set `GEMINI_API_KEY` in your environment (or Docker Compose) to enable narrative explanations."
            )

    # Load data: either synthetic or from uploaded CSV
    if data_mode == "Upload my own CSV" and uploaded_file is not None:
        events = pd.read_csv(uploaded_file)
        # Basic validation
        required_cols = {
            "timestamp",
            "latency_ms",
            "status_code",
            "region",
            "device",
            "endpoint",
        }
        if not required_cols.issubset(events.columns):
            st.error(
                f"Uploaded CSV missing required columns. Expected at least: {sorted(required_cols)}"
            )
            return
        events["timestamp"] = pd.to_datetime(events["timestamp"])
        windows = aggregate_windows(events, freq=freq)
        true_change_time = None
    else:
        with st.spinner("Generating synthetic production logs..."):
            events, windows, true_change_time = _generate_data(
                seed=seed, days=days, base_rpm=base_rpm, freq=freq
            )

    st.subheader("1. Timeline: when did the world shift?")

    detection = find_change_times(
        windows, metric_col=metric, time_col="timestamp", max_points=3
    )
    change_times = detection.change_times

    if windows.empty:
        st.warning("No data generated. Try increasing days or base traffic.")
        return

    metric_label = {
        "avg_latency_ms": "Average latency (ms)",
        "p95_latency_ms": "P95 latency (ms)",
        "error_rate": "Error rate",
    }[metric]

    chart_df = windows[["timestamp", metric]].rename(columns={metric: "value"})

    base_line = (
        alt.Chart(chart_df)
        .mark_line(color="#4e79a7")
        .encode(
            x=alt.X("timestamp:T", title="Time"),
            y=alt.Y("value:Q", title=metric_label),
            tooltip=["timestamp:T", "value:Q"],
        )
    )

    rules = []
    for ts in change_times:
        rules.append(
            alt.Chart(pd.DataFrame({"timestamp": [ts]}))
            .mark_rule(color="#e15759", strokeDash=[4, 4])
            .encode(x="timestamp:T")
        )

    timeline_chart = base_line
    for r in rules:
        timeline_chart = timeline_chart + r
    # Only show ground-truth line for synthetic data
    if true_change_time is not None:
        gt_rule = (
            alt.Chart(pd.DataFrame({"timestamp": [true_change_time]}))
            .mark_rule(color="#59a14f", strokeWidth=2)
            .encode(x="timestamp:T")
        )
        timeline_chart = timeline_chart + gt_rule

    st.altair_chart(timeline_chart.interactive(), width="stretch")

    if detection.drift_score is not None and not detection.drift_score.empty:
        drift_df = detection.drift_score.reset_index()
        drift_df.columns = ["timestamp", "drift_score"]
        drift_chart = (
            alt.Chart(drift_df)
            .mark_line(color="#f28e2b")
            .encode(
                x=alt.X("timestamp:T", title="Time"),
                y=alt.Y("drift_score:Q", title="Drift score"),
            )
        )
        st.altair_chart(drift_chart.interactive(), width="stretch")

    if true_change_time is not None:
        st.markdown(
            "_Green line = true hidden incident. Red dashed lines = detected breakpoints._"
        )
    else:
        st.markdown("_Red dashed lines = detected breakpoints in your uploaded data._")

    if not change_times:
        st.info("No strong breakpoints detected. Try increasing days or traffic.")
        return

    st.subheader("2. Pick a breakpoint to investigate")

    options = {f"{i+1}. {_format_ts(ts)}": ts for i, ts in enumerate(change_times)}
    label = st.selectbox("Detected breakpoints", list(options.keys()))
    selected_time = options[label]

    st.markdown(
        f"Investigating breakpoint at **{_format_ts(selected_time)}** "
        "(model-selected) vs injected ground truth."
    )

    st.subheader("3. Root-cause view: what actually changed?")

    with st.spinner("Computing before/after shifts and SHAP explanation..."):
        report = build_root_cause_report(
            events=events, change_time=selected_time.to_pydatetime(), window_minutes=60
        )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Avg latency (before, ms)", f"{report.latency_before:.1f}",
    )
    col2.metric(
        "Avg latency (after, ms)",
        f"{report.latency_after:.1f}",
        delta=f"{report.latency_after - report.latency_before:.1f}",
    )
    col3.metric(
        "Error rate (before)",
        f"{report.error_before*100:.2f}%",
    )
    col4.metric(
        "Error rate (after)",
        f"{report.error_after*100:.2f}%",
        delta=f"{(report.error_after - report.error_before)*100:.2f}%",
    )

    # Top affected segments
    if report.top_segments:
        seg_rows = [
            {
                "segment": s.key,
                "metric": s.metric,
                "before": s.before,
                "after": s.after,
                "delta": s.delta,
            }
            for s in report.top_segments
        ]
        seg_df = pd.DataFrame(seg_rows)
        st.markdown("### Most affected segments")
        # Plain dataframe to avoid matplotlib dependency in Styler.background_gradient
        st.dataframe(seg_df, width="stretch")
    else:
        st.info("No strong per-segment shifts detected in the incident window.")

    # SHAP feature importance chart
    if report.shap_importance:
        shap_df = pd.DataFrame(report.shap_importance)
        st.markdown("### Model-based drivers (SHAP importance)")
        shap_chart = (
            alt.Chart(shap_df)
            .mark_bar(color="#4e79a7")
            .encode(
                x=alt.X("importance:Q", title="Mean |SHAP|"),
                y=alt.Y("feature:N", sort="-x", title="Feature"),
                tooltip=["feature", "importance"],
            )
        )
        st.altair_chart(shap_chart, width="stretch")

    st.subheader("4. Narrative incident report (Gemini)")

    summary_stats = {
        "latency_before_ms": report.latency_before,
        "latency_after_ms": report.latency_after,
        "error_before": report.error_before,
        "error_after": report.error_after,
    }
    segment_dicts = [
        {
            "segment": s.key,
            "metric": s.metric,
            "before": s.before,
            "after": s.after,
            "delta": s.delta,
        }
        for s in report.top_segments
    ]

    cache_key = report.change_time.isoformat()
    gemini_cache = st.session_state["gemini_cache"]

    if st.button("Generate Gemini explanation", key=f"gemini-{cache_key}"):
        with st.spinner("Calling Gemini..."):
            explanation = explain_incident(
                change_time=report.change_time.isoformat(),
                summary_stats=summary_stats,
                top_segments=segment_dicts,
                shap_importance=report.shap_importance,
            )
            gemini_cache[cache_key] = explanation

    if cache_key in gemini_cache:
        st.markdown(gemini_cache[cache_key])
    else:
        st.caption(
            "Click the button above to generate a Gemini-powered incident summary. "
            "This avoids hitting rate limits on every parameter change."
        )

    st.subheader("5. Raw synthetic logs & downloads")
    with st.expander("Preview raw request logs (first 500 rows)"):
        st.dataframe(events.head(500), width="stretch")

    col_raw, col_win = st.columns(2)
    with col_raw:
        st.download_button(
            "Download raw events as CSV",
            data=events.to_csv(index=False).encode("utf-8"),
            file_name="synthetic_events.csv",
            mime="text/csv",
        )
    with col_win:
        st.download_button(
            "Download windowed metrics as CSV",
            data=windows.to_csv(index=False).encode("utf-8"),
            file_name="windowed_metrics.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()

