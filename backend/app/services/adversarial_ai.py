"""
Phase 03 — Adversarial AI Co-Pilot

Uses Claude to simulate adversary decision-making given the current battlespace picture,
surface risk vectors, and recommend adaptive friendly force actions.
"""
from __future__ import annotations

import json
import logging

import anthropic

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

_SYSTEM = """\
You are ATHENA, an adversarial AI co-pilot for C2D2 (Collaborative Combat Decision Dominance).
Your role is to simulate adversary behavior given a friendly force's operational picture,
identify risk vectors, and recommend adaptive actions.

Think like a red-team commander:
- Exploit gaps in friendly unit coverage
- Target logistics, communications, and command nodes
- Use terrain and timing to maximize disruption

Always respond in JSON matching the schema provided. Be tactically specific and realistic.
"""

_RESPONSE_SCHEMA = {
    "adversary_moves": [
        {
            "move_type": "flanking | ambush | direct_assault | indirect_fire | isr | cyber | deception",
            "description": "Specific adversary action description",
            "target": "Which friendly unit or asset is targeted",
            "timing": "When/how quickly this could occur",
            "probability": "high | medium | low",
        }
    ],
    "risk_vectors": [
        {
            "risk_type": "ambush | flanking | air_threat | supply_line | comms_disruption | overwatch_gap | flank_exposure",
            "severity": "critical | high | medium | low",
            "description": "Specific risk description",
            "affected_units": ["list of callsigns"],
            "recommended_action": "Specific action to mitigate this risk",
            "confidence_score": 0.0,
        }
    ],
    "recommendations": [
        {
            "priority": "immediate | short_term | monitor",
            "action": "Specific recommended action for friendly forces",
            "rationale": "Why this action is recommended",
        }
    ],
    "situation_summary": "2-3 sentence tactical summary of the adversary's most likely course of action",
}


def run_adversarial_simulation(session: dict) -> dict:
    """
    Run adversarial simulation on the current battlespace session.

    Args:
        session: Dict containing session_name, scenario_description, friendly_units,
                 known_enemy, intel_reports, sensor_tracks (list).

    Returns:
        Dict with adversary_moves, risk_vectors, recommendations, situation_summary.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — returning synthetic adversarial simulation")
        return _synthetic_simulation(session)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    friendly_str  = json.dumps(session.get("friendly_units") or [], indent=2)
    enemy_str     = json.dumps(session.get("known_enemy") or [], indent=2)
    intel_str     = json.dumps(session.get("intel_reports") or [], indent=2)
    tracks_str    = json.dumps(session.get("sensor_tracks") or [], indent=2)

    user_message = f"""\
BATTLESPACE SESSION: {session.get('session_name', 'Unknown')}
SCENARIO: {session.get('scenario_description', 'No description')}

FRIENDLY UNIT POSITIONS:
{friendly_str}

KNOWN ENEMY POSITIONS:
{enemy_str}

LIVE SENSOR TRACKS:
{tracks_str}

INTEL REPORTS:
{intel_str}

Analyze this battlespace as the adversary commander. Identify the most likely adversary courses
of action (max 4), surface the top risk vectors (max 5), and provide prioritized recommendations
for friendly forces.

Return JSON matching this schema exactly:
{json.dumps(_RESPONSE_SCHEMA, indent=2)}
"""

    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=2048,
            system=_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        result["ai_model_used"] = settings.claude_model
        return result
    except Exception as exc:
        logger.error("Adversarial simulation failed: %s", exc)
        return _synthetic_simulation(session)


def _synthetic_simulation(session: dict) -> dict:
    friendly = session.get("friendly_units") or []
    target = friendly[0].get("callsign", "Alpha") if friendly else "Alpha"
    return {
        "ai_model_used": "synthetic",
        "adversary_moves": [
            {
                "move_type": "flanking",
                "description": f"Adversary elements attempt to flank {target} from the northwest",
                "target": target,
                "timing": "Within 2 hours",
                "probability": "medium",
            }
        ],
        "risk_vectors": [
            {
                "risk_type": "flank_exposure",
                "severity": "high",
                "description": "Northern flank appears unguarded based on reported positions",
                "affected_units": [target],
                "recommended_action": "Position one team to secure northern approaches",
                "confidence_score": 0.65,
            }
        ],
        "recommendations": [
            {
                "priority": "immediate",
                "action": "Establish observation post on dominant terrain to the north",
                "rationale": "Current friendly positions leave northern approach unobserved",
            }
        ],
        "situation_summary": (
            "Adversary simulation unavailable (no API key configured). "
            "Synthetic placeholder: adversary most likely course of action is to exploit "
            "unobserved flanks. Configure ANTHROPIC_API_KEY for real simulation."
        ),
    }
