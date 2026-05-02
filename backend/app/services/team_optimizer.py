"""
Phase 02 — Team Optimization Engine

Scores soldiers for mission-specific fit using their skill vectors and mission parameters,
then generates ranked team compositions with Claude-powered explainable rationale.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

import anthropic

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

# Weights per mission type for each skill dimension
_MISSION_WEIGHTS: dict[str, dict[str, float]] = {
    "defend": {
        "leadership": 0.20, "decision_making": 0.15, "stress_tolerance": 0.20,
        "tactical": 0.20, "communication": 0.10, "teamwork": 0.10, "adaptability": 0.05,
    },
    "attack": {
        "leadership": 0.15, "decision_making": 0.20, "stress_tolerance": 0.15,
        "tactical": 0.25, "communication": 0.10, "teamwork": 0.10, "adaptability": 0.05,
    },
    "ambush": {
        "leadership": 0.10, "decision_making": 0.20, "stress_tolerance": 0.20,
        "tactical": 0.25, "communication": 0.05, "teamwork": 0.10, "adaptability": 0.10,
    },
    "raid": {
        "leadership": 0.20, "decision_making": 0.20, "stress_tolerance": 0.15,
        "tactical": 0.20, "communication": 0.10, "teamwork": 0.10, "adaptability": 0.05,
    },
    "mtc": {
        "leadership": 0.15, "decision_making": 0.20, "stress_tolerance": 0.15,
        "tactical": 0.20, "communication": 0.15, "teamwork": 0.10, "adaptability": 0.05,
    },
    "recon": {
        "leadership": 0.10, "decision_making": 0.15, "stress_tolerance": 0.15,
        "tactical": 0.25, "communication": 0.15, "teamwork": 0.05, "adaptability": 0.15,
    },
    "general": {
        "leadership": 0.17, "decision_making": 0.17, "stress_tolerance": 0.15,
        "tactical": 0.20, "communication": 0.12, "teamwork": 0.12, "adaptability": 0.07,
    },
}

# Threat level multipliers for stress_tolerance weight boost
_THREAT_BOOST: dict[str, float] = {
    "low": 0.0, "medium": 0.05, "high": 0.10, "extreme": 0.15
}


def score_soldier_fit(soldier_dict: dict, mission_type: str, threat_level: str = "medium") -> float:
    """
    Compute a 0.0–1.0 mission fit score for a single soldier.
    soldier_dict must include skill_* keys (0.0–1.0 scale).
    """
    weights = _MISSION_WEIGHTS.get(mission_type, _MISSION_WEIGHTS["general"]).copy()

    # Boost stress_tolerance weight for higher threat
    boost = _THREAT_BOOST.get(threat_level, 0.05)
    weights["stress_tolerance"] = min(weights["stress_tolerance"] + boost, 0.40)
    # Re-normalize
    total_w = sum(weights.values())
    weights = {k: v / total_w for k, v in weights.items()}

    skill_map = {
        "leadership": soldier_dict.get("skill_leadership", 0.5),
        "decision_making": soldier_dict.get("skill_decision_making", 0.5),
        "stress_tolerance": soldier_dict.get("skill_stress_tolerance", 0.5),
        "tactical": soldier_dict.get("skill_tactical", 0.5),
        "communication": soldier_dict.get("skill_communication", 0.5),
        "teamwork": soldier_dict.get("skill_teamwork", 0.5),
        "adaptability": soldier_dict.get("skill_adaptability", 0.5),
    }

    score = sum(weights[k] * skill_map[k] for k in weights)
    return round(score, 4)


def optimize_team(
    mission: dict,
    soldiers: list[dict],
    n_options: int = 3,
) -> list[dict]:
    """
    Generate up to n_options ranked team compositions for a mission.

    Args:
        mission: Dict with mission_type, threat_level, required_team_size, special_requirements…
        soldiers: List of soldier dicts (from DB) — all eligible (active) soldiers.
        n_options: Number of team options to return.

    Returns:
        List of composition dicts with {composition_rank, fit_score, rationale, members}.
    """
    mission_type = mission.get("mission_type", "general")
    threat_level = mission.get("threat_level", "medium")
    team_size    = mission.get("required_team_size", 9)
    special_reqs = set(mission.get("special_requirements") or [])

    # Score every soldier
    scored = []
    for s in soldiers:
        if not s.get("is_active", True):
            continue
        # Filter by special requirements
        soldier_quals = set(s.get("qualifications") or [])
        if special_reqs and not special_reqs.issubset(soldier_quals):
            continue
        fit = score_soldier_fit(s, mission_type, threat_level)
        scored.append((fit, s))

    scored.sort(key=lambda x: x[0], reverse=True)

    compositions = []
    for opt_idx in range(min(n_options, max(1, len(scored) - team_size + 1))):
        # Option 1: top-N, Option 2: slight variation (swap bottom slot), Option 3: further variation
        start_offset = opt_idx
        pool = scored[start_offset:]
        if len(pool) < team_size:
            break

        selected = pool[:team_size]
        avg_fit = sum(s[0] for s in selected) / len(selected)
        members = [
            {
                "soldier_id": s[1]["id"],
                "name": f"{s[1].get('rank','')} {s[1].get('name','')}".strip(),
                "unit": s[1].get("unit", ""),
                "fit_score": s[0],
                "role": _suggest_role(s[1], opt_idx),
            }
            for s in selected
        ]

        rationale = _generate_rationale(mission, members, avg_fit)
        compositions.append(
            {
                "composition_rank": opt_idx + 1,
                "fit_score": round(avg_fit, 4),
                "team_size": len(members),
                "rationale": rationale,
                "members": members,
            }
        )

    return compositions


def _suggest_role(soldier: dict, option_index: int) -> str:
    traits = (soldier.get("leadership_traits") or [])
    leader_type = soldier.get("leader_type", "")
    if "squad_leader" in leader_type or soldier.get("skill_leadership", 0) > 0.75:
        return "team_lead"
    if "medic" in leader_type or "68W" in (soldier.get("mos") or ""):
        return "medic"
    if "comms" in leader_type or "25" in (soldier.get("mos") or ""):
        return "comms"
    return "rifleman"


def _generate_rationale(mission: dict, members: list[dict], avg_fit: float) -> str:
    """Use Claude to write an explainable rationale; fall back to a template."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        return _template_rationale(mission, members, avg_fit)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = f"""\
Mission: {mission.get('mission_name','Unnamed')} ({mission.get('mission_type','general')}, {mission.get('threat_level','medium')} threat, {mission.get('terrain_type','general')} terrain)
Team average fit score: {avg_fit:.2f}/1.00

Team members:
{json.dumps([{"name": m["name"], "fit_score": m["fit_score"], "role": m["role"]} for m in members], indent=2)}

Write a 2-3 sentence rationale explaining why this team configuration is well-suited for the mission.
Focus on how the team's collective strengths match the mission requirements.
Be specific and actionable. Plain text, no markdown.
"""
    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as exc:
        logger.error("Rationale generation failed: %s", exc)
        return _template_rationale(mission, members, avg_fit)


def _template_rationale(mission: dict, members: list[dict], avg_fit: float) -> str:
    top = sorted(members, key=lambda m: m["fit_score"], reverse=True)[:3]
    names = ", ".join(m["name"] for m in top)
    return (
        f"Team achieves a composite fit score of {avg_fit:.0%} for this "
        f"{mission.get('mission_type','general')} mission. "
        f"Key contributors include {names}, selected for their high performance in "
        f"dimensions critical to {mission.get('terrain_type','general')} terrain "
        f"under {mission.get('threat_level','medium')} threat conditions."
    )
