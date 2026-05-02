"""
Phase 01 — AI Scoring Service

Uses Claude to analyze raw assessment text and return structured scores
for each leadership dimension, plus identified traits and decision style.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

import anthropic

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a military leadership assessment analyst for C2D2 (Collaborative Combat Decision Dominance).
You analyze field observations, instructor notes, and after-action review content to score soldier
performance across key leadership dimensions.

Always respond with valid JSON matching the schema provided. Be calibrated, fair, and evidence-based.
Scores are on a 0.0–5.0 scale (0=absent, 1=poor, 2=developing, 3=competent, 4=proficient, 5=expert).
"""

_SCORE_SCHEMA = {
    "score_leadership": "float 0-5 — overall leadership presence and effectiveness",
    "score_decision_quality": "float 0-5 — quality of decisions under pressure",
    "score_stress_response": "float 0-5 — composure and effectiveness under stress (5=excellent under stress)",
    "score_tactical": "float 0-5 — tactical proficiency and situational awareness",
    "score_communication": "float 0-5 — clarity and effectiveness of communication",
    "decision_style": "one of: aggressive | methodical | adaptive | defensive",
    "leadership_traits": "array of 2-5 trait strings (e.g. decisive, assertive, calm, strategic, empathetic)",
    "ai_summary": "2-3 sentence plain-English summary of overall performance highlighting strengths and gaps",
    "skill_vector_delta": {
        "leadership": "float -0.1 to 0.1 — suggested adjustment to cumulative skill",
        "decision_making": "float -0.1 to 0.1",
        "stress_tolerance": "float -0.1 to 0.1",
        "tactical": "float -0.1 to 0.1",
        "communication": "float -0.1 to 0.1",
        "teamwork": "float -0.1 to 0.1 — infer from observation",
        "adaptability": "float -0.1 to 0.1 — infer from observation",
    },
}


def score_assessment(raw_text: str, context: Optional[dict] = None) -> dict:
    """
    Analyze raw assessment text and return structured scores.

    Args:
        raw_text: The observation notes, OCR output, or STT transcript to analyze.
        context: Optional dict with soldier background (rank, unit, prior performance…).

    Returns:
        Dict with scores, traits, style, summary, and skill deltas.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — returning synthetic scores")
        return _synthetic_scores(raw_text)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    context_block = ""
    if context:
        context_block = f"\n\nSOLDIER CONTEXT:\n{json.dumps(context, indent=2)}"

    user_message = f"""\
ASSESSMENT TEXT TO ANALYZE:
{raw_text}
{context_block}

Return a JSON object matching this schema exactly:
{json.dumps(_SCORE_SCHEMA, indent=2)}
"""

    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as exc:
        logger.error("AI scoring failed: %s", exc)
        return _synthetic_scores(raw_text)


def _synthetic_scores(text: str) -> dict:
    """Fallback when no API key — returns mid-range scores with a note."""
    length_signal = min(len(text) / 500, 1.0)
    base = 2.5 + length_signal * 0.5
    return {
        "score_leadership": round(base, 1),
        "score_decision_quality": round(base - 0.2, 1),
        "score_stress_response": round(base - 0.1, 1),
        "score_tactical": round(base + 0.1, 1),
        "score_communication": round(base, 1),
        "decision_style": "methodical",
        "leadership_traits": ["disciplined", "dependable"],
        "ai_summary": "AI scoring unavailable (no API key configured). Scores are synthetic placeholders.",
        "skill_vector_delta": {
            "leadership": 0.0,
            "decision_making": 0.0,
            "stress_tolerance": 0.0,
            "tactical": 0.0,
            "communication": 0.0,
            "teamwork": 0.0,
            "adaptability": 0.0,
        },
    }
