"""
Training Schedule Generator — Phase 02

Produces a balanced 10-day platoon leadership rotation schedule.

Rules:
- 3 missions per day: planning, attack, defense
- 6 leadership roles per mission: PL, PSG, SL1, SL2, SL3, WSL
- No soldier leads in more than one mission per day
- Soldiers are matched to roles using skill vectors
- Assignments are balanced so each soldier leads approximately equally
"""
from __future__ import annotations

import random

MISSIONS = ["planning", "attack", "defense"]
ROLES    = ["PL", "PSG", "SL1", "SL2", "SL3", "WSL"]

# Primary + secondary skill weights per role
_ROLE_WEIGHTS: dict[str, dict[str, float]] = {
    "PL":  {"skill_leadership": 0.40, "skill_decision_making": 0.25,
            "skill_stress_tolerance": 0.20, "skill_communication": 0.15},
    "PSG": {"skill_leadership": 0.25, "skill_decision_making": 0.30,
            "skill_stress_tolerance": 0.25, "skill_tactical": 0.20},
    "SL1": {"skill_tactical": 0.35, "skill_leadership": 0.30,
            "skill_communication": 0.20, "skill_teamwork": 0.15},
    "SL2": {"skill_tactical": 0.35, "skill_leadership": 0.30,
            "skill_communication": 0.20, "skill_adaptability": 0.15},
    "SL3": {"skill_tactical": 0.35, "skill_leadership": 0.30,
            "skill_communication": 0.20, "skill_stress_tolerance": 0.15},
    "WSL": {"skill_technical": 0.40, "skill_tactical": 0.30,
            "skill_leadership": 0.20, "skill_physical": 0.10},
}


def _skill_score(soldier: dict, role: str) -> float:
    weights = _ROLE_WEIGHTS.get(role, {"skill_leadership": 1.0})
    return sum(soldier.get(sk, 0.5) * w for sk, w in weights.items())


def generate_schedule(soldiers: list[dict], num_days: int = 10, seed: int | None = None) -> list[dict]:
    """
    Generate a fair leadership rotation schedule.

    Args:
        soldiers: List of soldier dicts — must include ``id`` and skill fields.
        num_days: Training period length (default 10).
        seed:     Optional RNG seed for reproducibility.

    Returns:
        List of slot dicts: {day_number, mission_type, role, soldier_id}.
    """
    if seed is not None:
        random.seed(seed)

    n = len(soldiers)
    if n == 0:
        return []

    lead_count: dict[int, int]              = {s["id"]: 0 for s in soldiers}
    role_count: dict[int, dict[str, int]]   = {s["id"]: {r: 0 for r in ROLES} for s in soldiers}

    slots: list[dict] = []

    for day in range(1, num_days + 1):
        daily_assigned: set[int] = set()

        for mission in MISSIONS:
            for role in ROLES:
                available = [s for s in soldiers if s["id"] not in daily_assigned]

                # If all soldiers have led today, allow repeats (unlikely with 32+ soldiers)
                if not available:
                    available = list(soldiers)

                total_leads = sum(lead_count.values()) or 1
                avg_leads   = total_leads / n

                def _score(s: dict, _role: str = role) -> float:
                    sid = s["id"]
                    skill      = _skill_score(s, _role)
                    # Reward under-assigned soldiers (fairness)
                    fairness   = (avg_leads - lead_count[sid]) * 0.4
                    # Reward trying a new role type (variety)
                    variety    = 0.25 if role_count[sid][_role] == 0 else 0.0
                    # Small random jitter so ties don't always resolve the same way
                    jitter     = random.uniform(0, 0.05)
                    return skill + fairness + variety + jitter

                best = max(available, key=_score)
                sid  = best["id"]

                daily_assigned.add(sid)
                lead_count[sid]            += 1
                role_count[sid][role]      += 1

                slots.append({
                    "day_number":   day,
                    "mission_type": mission,
                    "role":         role,
                    "soldier_id":   sid,
                })

    return slots


def lead_summary(slots: list[dict], soldiers: list[dict]) -> list[dict]:
    """
    Build a per-soldier leadership summary from a list of slots.

    Returns list of {soldier_id, name, lead_count, roles_played, command_count}
    sorted by soldier_id.
    """
    soldier_map = {s["id"]: s for s in soldiers}
    summary: dict[int, dict] = {}

    for s in soldiers:
        summary[s["id"]] = {
            "soldier_id":     s["id"],
            "name":           f"{s.get('rank','')} {s.get('name','')}".strip(),
            "lead_count":     0,
            "command_count":  0,   # PL or PSG appearances
            "roles_played":   {},  # role -> count
        }

    for slot in slots:
        sid  = slot["soldier_id"]
        role = slot["role"]
        if sid not in summary:
            continue
        summary[sid]["lead_count"]  += 1
        summary[sid]["roles_played"][role] = summary[sid]["roles_played"].get(role, 0) + 1
        if role in ("PL", "PSG"):
            summary[sid]["command_count"] += 1

    return sorted(summary.values(), key=lambda x: x["soldier_id"])
