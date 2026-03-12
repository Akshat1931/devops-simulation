from __future__ import annotations

import os
import time  # <-- CHANGED
from typing import List, Dict, Any

from google import genai
from google.genai import types


# ----------------------------
# Global Gemini client (singleton)
# ----------------------------
_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")  # <-- CHANGED
_CLIENT = genai.Client(api_key=_API_KEY) if _API_KEY else None         # <-- CHANGED
_LAST_CALL = 0.0                                                      # <-- CHANGED


def _fallback_explanation(
    change_time: str,
    summary_stats: Dict[str, Any],
    top_segments: List[Dict[str, Any]],
) -> str:
    """Simple built-in narrative if Gemini is unavailable or errors."""
    lat_before = summary_stats.get("latency_before_ms") or summary_stats.get(
        "latency_before"
    )
    lat_after = summary_stats.get("latency_after_ms") or summary_stats.get(
        "latency_after"
    )
    err_before = summary_stats.get("error_before")
    err_after = summary_stats.get("error_after")

    main_seg = top_segments[0] if top_segments else None

    lines = []
    lines.append(f"**Incident time**: {change_time}")
    if lat_before is not None and lat_after is not None:
        lines.append(
            f"- Average latency jumped from ~{lat_before:.1f} ms to ~{lat_after:.1f} ms."
        )
    if err_before is not None and err_after is not None:
        lines.append(
            f"- Error rate changed from ~{err_before*100:.2f}% to ~{err_after*100:.2f}%."
        )

    if main_seg:
        lines.append(
            f"- Most affected segment: **{main_seg['segment']}** on metric "
            f"**{main_seg['metric']}** (Δ={main_seg['delta']:.3f})."
        )

    lines.append("")
    lines.append("**Likely cause & next steps (heuristic)**")
    lines.append(
        "- A specific combination of endpoint / region / device started behaving worse "
        "around the detected time."
    )
    if main_seg and "endpoint" in main_seg["segment"]:
        lines.append(
            "- Check recent deployments, config changes, or feature flags touching this endpoint."
        )
    lines.append(
        "- Inspect logs and traces for this segment around the incident time to confirm "
        "whether timeouts, dependency failures, or traffic spikes align with this jump."
    )

    return "\n".join(lines)


def explain_incident(
    change_time: str,
    summary_stats: Dict[str, Any],
    top_segments: List[Dict[str, Any]],
    shap_importance: List[Dict[str, Any]],
) -> str:
    """
    Use Gemini (via google.genai) to turn numeric diagnostics into a human incident narrative.
    Env vars:
    - GOOGLE_API_KEY (preferred)
    - GEMINI_API_KEY (fallback)
    - GEMINI_MODEL_NAME or GENAI_MODEL_NAME to override the model
    """
    if not _CLIENT:  # <-- CHANGED
        return _fallback_explanation(change_time, summary_stats, top_segments)

    raw_model = (
        os.getenv("GEMINI_MODEL_NAME")
        or os.getenv("GENAI_MODEL_NAME")
        or "gemini-1.5-flash"  # <-- CHANGED (more widely available, lower quota usage)
    )
    model_name = raw_model

    global _LAST_CALL  # <-- CHANGED
    now = time.time()
    if now - _LAST_CALL < 3.0:  # <-- CHANGED (rate limit)
        time.sleep(3.0 - (now - _LAST_CALL))
    _LAST_CALL = time.time()

    try:
        prompt = (
            "You are helping an SRE / MLOps engineer understand an incident detected in "
            "production-like logs. Write a concise but actionable incident summary.\n\n"
            f"Change time (UTC): {change_time}\n\n"
            "High-level metrics before vs after the change:\n"
            f"{summary_stats}\n\n"
            "Top segments with the largest metric shifts (key, metric, before, after, delta):\n"
            f"{top_segments}\n\n"
            "Top SHAP feature importances (feature, importance):\n"
            f"{shap_importance}\n\n"
            "Tasks:\n"
            "1) Explain in plain language what most likely changed in the system.\n"
            "2) Call out the main impacted slice (endpoint/region/device) and how.\n"
            "3) Suggest 2-3 plausible root causes or hypotheses.\n"
            "4) Suggest 2-3 concrete next debugging or mitigation steps.\n"
            "5) Keep it under 250 words.\n"
        )

        # Try simpler API call without config
        response = _CLIENT.models.generate_content(
            model=model_name,
            contents=prompt,
        )

        if not response or not response.text:  # <-- CHANGED
            raise RuntimeError("Empty Gemini response")

        return response.text

    except Exception as exc:  # noqa: BLE001
        fallback = _fallback_explanation(change_time, summary_stats, top_segments)
        error_msg = str(exc)
        error_type = type(exc).__name__
        
        # Debug: print full error for troubleshooting
        import sys
        print(f"DEBUG Gemini Error: {error_type}: {error_msg}", file=sys.stderr)
        
        # Provide specific guidance for common errors
        if "400" in error_msg or "BadRequest" in error_msg:
            hint = "Check API key validity and model name"
        elif "429" in error_msg or "TooManyRequests" in error_msg:
            hint = "API quota exceeded - wait or upgrade quota"
        elif "403" in error_msg or "Forbidden" in error_msg:
            hint = "API key lacks permission for this model"
        else:
            hint = f"Check GOOGLE_API_KEY env var | Error: {error_msg[:100]}"
        
        return (
            f"_(Gemini explanation unavailable: {error_type} - {hint})_\n\n"
            f"{fallback}"
        )