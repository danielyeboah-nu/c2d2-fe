"""
Phase 02 — Team Optimization Engine

Scores soldiers for mission-specific fit using their skill vectors, mission parameters,
and real-time ATAK context (sleep/readiness, weather conditions).
Generates ranked team compositions with Claude-powered explainable rationale.
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

# Operational statuses that disqualify a soldier from selection
_UNAVAILABLE_STATUSES = {"on_mission", "casualty"}


def score_soldier_fit(soldier_dict: dict, mission_type: str, threat_level: str = "medium") -> float:
    """
    Compute a 0.0–1.0 base mission fit score for a single soldier.
    soldier_dict must include skill_* keys (0.0–1.0 scale).
    Does not apply readiness or weather modifiers — use optimize_team for contextual scoring.
    """
    weights = _MISSION_WEIGHTS.get(mission_type, _MISSION_WEIGHTS["general"]).copy()

    boost = _THREAT_BOOST.get(threat_level, 0.05)
    weights["stress_tolerance"] = min(weights["stress_tolerance"] + boost, 0.40)
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

    return round(sum(weights[k] * skill_map[k] for k in weights), 4)


def _readiness_modifier(sleep_hours_24h: float, injury_status: str = "fit") -> tuple[float, str | None]:
    """
    Returns (multiplier, human-readable note).
    Based on USARIEM sleep deprivation performance curves.
    """
    if injury_status == "unfit":
        return 0.0, "unfit for duty"

    injury_mult = 0.70 if injury_status == "light_duty" else 1.0

    if sleep_hours_24h >= 8:    sleep_mult = 1.00
    elif sleep_hours_24h >= 7:  sleep_mult = 0.95
    elif sleep_hours_24h >= 6:  sleep_mult = 0.85
    elif sleep_hours_24h >= 4:  sleep_mult = 0.75
    else:                        sleep_mult = 0.60

    total = round(injury_mult * sleep_mult, 3)
    if total >= 1.0:
        return total, None

    parts = []
    if sleep_mult < 1.0:
        parts.append(f"{sleep_hours_24h:.1f}h sleep")
    if injury_status == "light_duty":
        parts.append("light duty")
    return total, f"Readiness ×{total:.2f} ({', '.join(parts)})"


def _weather_modifier(weather: dict) -> tuple[float, str | None]:
    """Returns (multiplier, human-readable note) based on AO weather conditions."""
    mult = 1.0
    reasons: list[str] = []

    wbgt = weather.get("wbgt") or 0.0
    temp = weather.get("temperature_c") or 20.0
    vis  = weather.get("visibility_km") or 10.0

    if wbgt > 32:
        mult *= 0.80
        reasons.append(f"WBGT {wbgt:.0f}°C heat stress")
    elif wbgt > 28:
        mult *= 0.90
        reasons.append(f"WBGT {wbgt:.0f}°C heat caution")

    if temp < -10:
        mult *= 0.85
        reasons.append(f"{temp:.0f}°C cold ops")

    if vis < 1.0:
        mult *= 0.90
        reasons.append(f"{vis:.1f}km visibility")

    mult = round(mult, 3)
    note = f"Weather ×{mult:.2f} ({', '.join(reasons)})" if reasons else None
    return mult, note


def optimize_team(
    mission: dict,
    soldiers: list[dict],
    n_options: int = 3,
    readiness_map: dict[int, dict] | None = None,
    weather: dict | None = None,
) -> list[dict]:
    """
    Generate up to n_options ranked team compositions for a mission.

    Args:
        mission:       Dict with mission_type, threat_level, required_team_size, etc.
        soldiers:      All active soldiers as dicts (from DB).
        n_options:     Number of ranked alternatives to return.
        readiness_map: {soldier_id: {sleep_hours_24h, injury_status, operational_status, ...}}
        weather:       Weather snapshot dict for the AO (temperature_c, wbgt, visibility_km, ...).

    Returns:
        List of composition dicts with contextual fit scores and modifier notes.
    """
    mission_type = mission.get("mission_type", "general")
    threat_level = mission.get("threat_level", "medium")
    team_size    = mission.get("required_team_size", 9)
    special_reqs = set(mission.get("special_requirements") or [])
    readiness_map = readiness_map or {}

    scored: list[tuple[float, float, list[str], dict]] = []  # (contextual, base, notes, soldier)

    for s in soldiers:
        if not s.get("is_active", True):
            continue

        soldier_id = s["id"]
        readiness  = readiness_map.get(soldier_id, {})

        # Exclude soldiers who are unavailable
        if readiness.get("operational_status") in _UNAVAILABLE_STATUSES:
            continue

        soldier_quals = set(s.get("qualifications") or [])
        if special_reqs and not special_reqs.issubset(soldier_quals):
            continue

        base_fit = score_soldier_fit(s, mission_type, threat_level)
        contextual_fit = base_fit
        modifier_notes: list[str] = []

        if readiness:
            r_mult, r_note = _readiness_modifier(
                readiness.get("sleep_hours_24h", 8.0),
                readiness.get("injury_status", "fit"),
            )
            # Zero multiplier means unfit — exclude entirely
            if r_mult == 0.0:
                continue
            contextual_fit *= r_mult
            if r_note:
                modifier_notes.append(r_note)

        if weather:
            w_mult, w_note = _weather_modifier(weather)
            contextual_fit *= w_mult
            if w_note:
                modifier_notes.append(w_note)

        scored.append((round(contextual_fit, 4), base_fit, modifier_notes, s))

    scored.sort(key=lambda x: x[0], reverse=True)

    compositions = []
    for opt_idx in range(min(n_options, max(1, len(scored) - team_size + 1))):
        pool = scored[opt_idx:]
        if len(pool) < team_size:
            break

        selected = pool[:team_size]
        avg_fit  = sum(s[0] for s in selected) / len(selected)

        members = [
            {
                "soldier_id":     s[3]["id"],
                "name":           f"{s[3].get('rank', '')} {s[3].get('name', '')}".strip(),
                "unit":           s[3].get("unit", ""),
                "fit_score":      s[0],
                "base_fit_score": s[1],
                "fit_notes":      "; ".join(s[2]) if s[2] else None,
                "role":           _suggest_role(s[3], opt_idx),
            }
            for s in selected
        ]

        rationale = _generate_rationale(mission, members, avg_fit, weather)
        compositions.append(
            {
                "composition_rank": opt_idx + 1,
                "fit_score":        round(avg_fit, 4),
                "team_size":        len(members),
                "rationale":        rationale,
                "members":          members,
            }
        )

    return compositions


def _suggest_role(soldier: dict, option_index: int) -> str:
    leader_type = soldier.get("leader_type", "")
    if "squad_leader" in leader_type or soldier.get("skill_leadership", 0) > 0.75:
        return "team_lead"
    if "medic" in leader_type or "68W" in (soldier.get("mos") or ""):
        return "medic"
    if "comms" in leader_type or "25" in (soldier.get("mos") or ""):
        return "comms"
    return "rifleman"


def _generate_rationale(
    mission: dict,
    members: list[dict],
    avg_fit: float,
    weather: dict | None = None,
) -> str:
    """Use Claude to write an explainable rationale; fall back to a template."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        return _template_rationale(mission, members, avg_fit, weather)

    degraded = [m for m in members if m.get("fit_notes")]
    weather_ctx = ""
    if weather:
        parts = []
        if weather.get("wbgt"):
            parts.append(f"WBGT {weather['wbgt']:.0f}°C")
        if weather.get("temperature_c") is not None:
            parts.append(f"{weather['temperature_c']:.0f}°C")
        if weather.get("visibility_km") is not None:
            parts.append(f"{weather['visibility_km']:.1f}km visibility")
        if parts:
            weather_ctx = f"\nAO weather: {', '.join(parts)}"

    readiness_ctx = ""
    if degraded:
        readiness_ctx = "\nReadiness notes:\n" + "\n".join(
            f"  - {m['name']}: {m['fit_notes']}" for m in degraded
        )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = f"""\
Mission: {mission.get('mission_name', 'Unnamed')} ({mission.get('mission_type', 'general')}, {mission.get('threat_level', 'medium')} threat, {mission.get('terrain_type', 'general')} terrain)
Team contextual fit score: {avg_fit:.2f}/1.00{weather_ctx}{readiness_ctx}

Team members:
{json.dumps([{"name": m["name"], "fit_score": m["fit_score"], "base_fit_score": m["base_fit_score"], "role": m["role"]} for m in members], indent=2)}

Write a 2-3 sentence rationale explaining why this team configuration is well-suited for the mission.
If readiness or weather modifiers reduced any soldier's score, briefly acknowledge the operational context.
Be specific and actionable. Plain text, no markdown.
"""
    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as exc:
        logger.error("Rationale generation failed: %s", exc)
        return _template_rationale(mission, members, avg_fit, weather)


def _template_rationale(
    mission: dict,
    members: list[dict],
    avg_fit: float,
    weather: dict | None = None,
) -> str:
    top   = sorted(members, key=lambda m: m["fit_score"], reverse=True)[:3]
    names = ", ".join(m["name"] for m in top)
    base  = (
        f"Team achieves a contextual fit score of {avg_fit:.0%} for this "
        f"{mission.get('mission_type', 'general')} mission. "
        f"Key contributors include {names}, selected for performance in dimensions "
        f"critical to {mission.get('terrain_type', 'general')} terrain under "
        f"{mission.get('threat_level', 'medium')} threat conditions."
    )
    degraded = [m for m in members if m.get("fit_notes")]
    if degraded:
        base += f" Note: {len(degraded)} soldier(s) have reduced readiness scores factored into selection."
    return base
