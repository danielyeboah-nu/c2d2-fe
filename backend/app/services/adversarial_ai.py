"""
Phase 03 — Adversarial AI Co-Pilot

Uses Claude to simulate adversary decision-making given the current battlespace picture,
surface risk vectors, and produce a full simulation report including squad-level and
individual-level performance analysis.
"""
from __future__ import annotations

import json
import logging

import anthropic

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

_SYSTEM = """\
You are ATHENA, an adversarial AI co-pilot for C2D2 (Combat Decision Dominance).
Your dual role is:
  1. Red-team commander — simulate the adversary's most likely courses of action
     given the battlespace picture, exploiting friendly gaps and weaknesses.
  2. Force analyst — assess the assembled squad's ability to execute this mission
     given each soldier's skill profile, current readiness, and the environmental
     conditions (terrain, weather, duration, threat level).

Think like a seasoned S3:
- Identify the adversary's best opportunities before the friendly force closes them.
- Cross-reference each squad member's specific strengths and weaknesses against
  this mission's demands. A high-physical soldier matters more in mountain terrain;
  high-stress-tolerance matters more in a high-threat ambush scenario.
- Factor in fatigue and injury realistically: a soldier at 0.7 fatigue index is
  significantly degraded; an "unfit" injury status is a mission-critical liability.
- Weather and terrain interact with skill vectors — highlight those interactions
  specifically (e.g., poor visibility degrades communication; extreme heat amplifies
  fatigue penalties on physical soldiers).

Always respond in valid JSON matching the schema provided. Be tactically specific.
"""

_RESPONSE_SCHEMA = {
    "outcome_verdict": "likely_success | marginal | likely_failure",
    "outcome_confidence": 0.75,
    "situation_summary": "2–3 sentence tactical summary of the overall situation",
    "adversary_moves": [
        {
            "move_type": "flanking | ambush | direct_assault | indirect_fire | isr | cyber | deception",
            "description": "Specific adversary action",
            "target": "Which friendly unit or asset is targeted",
            "timing": "When this could occur",
            "probability": "high | medium | low",
        }
    ],
    "risk_vectors": [
        {
            "risk_type": "ambush | flanking | air_threat | supply_line | comms_disruption | overwatch_gap | flank_exposure",
            "severity": "critical | high | medium | low",
            "description": "Specific risk description tied to squad/terrain/readiness factors",
            "affected_units": ["callsign"],
            "recommended_action": "Concrete mitigation action",
            "confidence_score": 0.0,
        }
    ],
    "recommendations": [
        {
            "priority": "immediate | short_term | monitor",
            "action": "Specific action for friendly forces",
            "rationale": "Why, referencing squad or environmental data",
        }
    ],
    "squad_assessment": {
        "overall_readiness": "One-sentence collective readiness verdict",
        "team_fit_score": 0.75,
        "critical_gaps": ["gap 1", "gap 2"],
        "members": [
            {
                "name": "SGT Smith",
                "role": "team_lead",
                "fit_score": 0.82,
                "key_strengths": ["leadership", "tactical"],
                "key_weaknesses": ["stress_tolerance"],
                "readiness_note": "Specific impact of this soldier's fatigue/injury on this mission",
                "mission_contribution": "positive | neutral | liability",
                "recommendation": "Actionable note for this soldier",
            }
        ],
    },
    "environmental_factors": [
        {
            "factor": "terrain | weather | duration | threat_level",
            "label": "Urban Terrain",
            "impact": "How this factor specifically affects this squad and their skill mix",
            "severity": "high | medium | low",
            "affected_skills": ["tactical", "communication"],
        }
    ],
}


def run_adversarial_simulation(session: dict) -> dict:
    """
    Run adversarial simulation on the current battlespace session.

    Args:
        session: Dict containing session_name, scenario_description, friendly_units,
                 known_enemy, intel_reports, sensor_tracks, squad_members (optional),
                 mission_context (optional).

    Returns:
        Dict matching the full report schema above.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — returning synthetic adversarial simulation")
        return _synthetic_simulation(session)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    friendly_str = json.dumps(session.get("friendly_units") or [], indent=2)
    enemy_str    = json.dumps(session.get("known_enemy") or [], indent=2)
    intel_str    = json.dumps(session.get("intel_reports") or [], indent=2)
    tracks_str   = json.dumps(session.get("sensor_tracks") or [], indent=2)

    # Squad members section (populated when session is linked to a mission with a team)
    squad_str = ""
    if session.get("squad_members"):
        squad_str = f"""
ASSEMBLED SQUAD ({len(session['squad_members'])} members):
{json.dumps(session['squad_members'], indent=2)}

Squad skill key: all values are 0.0–1.0 (1.0 = expert).
Fatigue index: 0.0 = fully rested, 1.0 = severely fatigued.
Injury status: fit | light_duty | unfit.
"""

    # Mission context section
    ctx_str = ""
    if session.get("mission_context"):
        ctx_str = f"""
MISSION CONTEXT:
{json.dumps(session['mission_context'], indent=2)}
"""

    user_message = f"""\
BATTLESPACE SESSION: {session.get('session_name', 'Unknown')}
SCENARIO: {session.get('scenario_description', 'No description provided')}
{ctx_str}
FRIENDLY UNIT POSITIONS:
{friendly_str}

KNOWN ENEMY POSITIONS:
{enemy_str}

LIVE SENSOR TRACKS:
{tracks_str}

INTEL REPORTS:
{intel_str}
{squad_str}
Analyze this battlespace as both the adversary commander and the friendly force analyst.

For the adversary analysis: identify the most likely adversary courses of action (max 4),
the top risk vectors (max 5), and prioritised recommendations.

For the squad assessment: evaluate each squad member's suitability for this specific mission
given their skill profile, current readiness, and the mission environment. Identify collective
gaps. Rate overall outcome likelihood.

For environmental factors: explain how each significant environmental factor (terrain, weather,
duration, threat level) specifically interacts with THIS squad's skill mix and readiness state.

Return JSON matching this schema exactly — no prose outside the JSON:
{json.dumps(_RESPONSE_SCHEMA, indent=2)}
"""

    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=4096,
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
    squad    = session.get("squad_members") or []
    target   = friendly[0].get("callsign", "Alpha") if friendly else "Alpha"

    member_assessments = []
    for m in squad:
        skills = m.get("skills", {})
        strengths  = sorted(skills, key=lambda k: skills[k], reverse=True)[:2]
        weaknesses = sorted(skills, key=lambda k: skills[k])[:2]
        fi = m.get("fatigue_index")
        member_assessments.append({
            "name": m.get("name", "Unknown"),
            "role": m.get("role", "rifleman"),
            "fit_score": m.get("fit_score", 0.5),
            "key_strengths": strengths,
            "key_weaknesses": weaknesses,
            "readiness_note": (
                f"Fatigue index {fi:.2f} — performance degraded" if fi and fi > 0.4
                else "Readiness within acceptable limits"
            ) if fi is not None else "No readiness data available",
            "mission_contribution": (
                "liability" if (fi or 0) > 0.65 or m.get("injury_status") == "unfit"
                else "neutral" if (fi or 0) > 0.35
                else "positive"
            ),
            "recommendation": (
                "Consider resting before mission execution"
                if (fi or 0) > 0.5 else "Ready to deploy"
            ),
        })

    return {
        "ai_model_used": "synthetic",
        "outcome_verdict": "marginal",
        "outcome_confidence": 0.45,
        "situation_summary": (
            "Synthetic simulation — configure ANTHROPIC_API_KEY for real AI analysis. "
            "Adversary most likely course of action is to exploit unobserved flanks "
            f"and target {target}."
        ),
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
        "squad_assessment": {
            "overall_readiness": (
                f"{len(squad)} members assessed — synthetic data only"
                if squad else "No squad composition linked to this session"
            ),
            "team_fit_score": (
                sum(m.get("fit_score", 0.5) for m in squad) / len(squad)
                if squad else 0.0
            ),
            "critical_gaps": ["Flank security", "Comms redundancy"],
            "members": member_assessments,
        },
        "environmental_factors": [
            {
                "factor": "terrain",
                "label": "Unknown Terrain",
                "impact": "Terrain analysis requires real simulation. Configure API key.",
                "severity": "medium",
                "affected_skills": ["tactical"],
            }
        ],
    }
