"""
Phase 01 — Performance Analysis endpoints.

Individual Leader Analysis, Unit Collective Analysis, Battalion Overview.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import Assessment, DetailedRating, Soldier, TrainingEvent, User
from backend.app.deps import get_current_user
from backend.app.services.eval_reference import LEADER_EVAL, STEO_MISSIONS, UNIT_EVAL, get_reference

router = APIRouter(prefix="/analysis", tags=["Analysis — Phase 01"])

LEADER_FIELDS = ["ldr_planning", "ldr_atd", "ldr_time_mgmt", "ldr_decisiveness", "ldr_tactics"]
UMP_FIELDS    = ["ump_planning", "ump_atd", "ump_time_mgmt", "ump_decisiveness", "ump_tactics"]
LEADER_LABELS = ["Planning", "Attn to Detail", "Time Mgmt", "Decisiveness", "Tactics"]


def _ldr_scores(a: Assessment) -> dict[str, float | None]:
    return {
        "Planning":       a.ldr_planning,
        "Attn to Detail": a.ldr_atd,
        "Time Mgmt":      a.ldr_time_mgmt,
        "Decisiveness":   a.ldr_decisiveness,
        "Tactics":        a.ldr_tactics,
    }


def _ump_scores(a: Assessment) -> dict[str, float | None]:
    return {
        "Planning":       a.ump_planning,
        "Attn to Detail": a.ump_atd,
        "Time Mgmt":      a.ump_time_mgmt,
        "Decisiveness":   a.ump_decisiveness,
        "Tactics":        a.ump_tactics,
    }


def _event_label(a: Assessment) -> str:
    if a.event:
        return a.event.event_name
    return a.created_at.strftime("%Y-%m-%d") if a.created_at else str(a.id)


def _steo_proficiency(avg: float) -> str:
    if avg >= 4.5:   return "T"
    if avg >= 3.75:  return "P+"
    if avg >= 3.0:   return "P"
    if avg >= 2.0:   return "P-"
    return "U"


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

@router.get("/reference/{eval_type}")
def eval_reference(eval_type: str, _: User = Depends(get_current_user)):
    data = get_reference(eval_type)
    if not data:
        raise HTTPException(404, detail="Unknown eval type")
    return data


# ---------------------------------------------------------------------------
# Individual Leader Analysis
# ---------------------------------------------------------------------------

@router.get("/leader/{soldier_id}")
def leader_analysis(
    soldier_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    soldier = db.query(Soldier).filter(Soldier.id == soldier_id).first()
    if not soldier:
        raise HTTPException(404, detail="Soldier not found")

    assessments = (
        db.query(Assessment)
        .filter(Assessment.soldier_id == soldier_id)
        .order_by(Assessment.created_at.asc())
        .all()
    )

    # ------------------------------------------------------------------
    # Averages
    # ------------------------------------------------------------------
    ldr_sums: dict[str, list[float]] = defaultdict(list)
    ump_sums: dict[str, list[float]] = defaultdict(list)

    for a in assessments:
        for label, val in _ldr_scores(a).items():
            if val is not None:
                ldr_sums[label].append(val)
        for label, val in _ump_scores(a).items():
            if val is not None:
                ump_sums[label].append(val)

    ldr_avg = {k: round(sum(v) / len(v), 2) for k, v in ldr_sums.items() if v}
    ump_avg = {k: round(sum(v) / len(v), 2) for k, v in ump_sums.items() if v}

    # ------------------------------------------------------------------
    # Trend data (per evaluation, chronological)
    # ------------------------------------------------------------------
    ldr_trend: list[dict] = []
    ump_trend: list[dict] = []

    for a in assessments:
        label = _event_label(a)
        ls = _ldr_scores(a)
        us = _ump_scores(a)
        if any(v is not None for v in ls.values()):
            ldr_trend.append({"event": label, **{k: v for k, v in ls.items() if v is not None}})
        if any(v is not None for v in us.values()):
            ump_trend.append({"event": label, **{k: v for k, v in us.items() if v is not None}})

    # ------------------------------------------------------------------
    # ST&EO proficiency by mission
    # ------------------------------------------------------------------
    steo_buckets: dict[str, list[float]] = defaultdict(list)

    steo_assessments = [a for a in assessments if a.eval_category == "steo_eval"]
    for a in steo_assessments:
        ratings = db.query(DetailedRating).filter(DetailedRating.assessment_id == a.id).all()
        scores = [r.rating_score for r in ratings if r.rating_score]
        if scores and a.steo_mission_name:
            steo_buckets[a.steo_mission_name].append(sum(scores) / len(scores))

    steo_summary = [
        {
            "mission": mission,
            "avg_score": round(sum(vals) / len(vals), 2),
            "proficiency": _steo_proficiency(sum(vals) / len(vals)),
            "eval_count": len(vals),
        }
        for mission, vals in steo_buckets.items()
    ]

    # ------------------------------------------------------------------
    # AI score averages
    # ------------------------------------------------------------------
    ai_fields = ["score_leadership", "score_decision_quality", "score_stress_response",
                 "score_tactical", "score_communication"]
    ai_sums: dict[str, list[float]] = defaultdict(list)
    for a in assessments:
        for f in ai_fields:
            v = getattr(a, f, None)
            if v is not None:
                ai_sums[f].append(v)
    ai_avg = {k: round(sum(v) / len(v), 2) for k, v in ai_sums.items() if v}

    return {
        "soldier": {
            "id": soldier.id,
            "rank": soldier.rank,
            "name": soldier.name,
            "unit": soldier.unit,
            "mos": soldier.mos,
        },
        "eval_count": len(assessments),
        "leader_averages": ldr_avg,
        "ump_averages": ump_avg,
        "ai_averages": ai_avg,
        "leader_trend": ldr_trend,
        "ump_trend": ump_trend,
        "steo_summary": steo_summary,
        "assessments": [
            {
                "id": a.id,
                "event": _event_label(a),
                "eval_category": a.eval_category,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                **{k: v for k, v in _ldr_scores(a).items() if v is not None},
                **{f"ump_{k}": v for k, v in _ump_scores(a).items() if v is not None},
                "ai_summary": a.ai_summary,
            }
            for a in assessments
        ],
    }


# ---------------------------------------------------------------------------
# Unit Collective Analysis
# ---------------------------------------------------------------------------

@router.get("/unit")
def unit_analysis(
    unit: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    soldiers = db.query(Soldier).filter(Soldier.unit == unit, Soldier.is_active == True).all()
    if not soldiers:
        raise HTTPException(404, detail="No active soldiers found for that unit")

    soldier_ids = [s.id for s in soldiers]
    all_assessments = (
        db.query(Assessment)
        .filter(Assessment.soldier_id.in_(soldier_ids))
        .order_by(Assessment.created_at.asc())
        .all()
    )

    # Per-soldier averages
    per_soldier: list[dict] = []
    for s in soldiers:
        s_assessments = [a for a in all_assessments if a.soldier_id == s.id]
        ldr_sums: dict[str, list[float]] = defaultdict(list)
        ump_sums: dict[str, list[float]] = defaultdict(list)
        for a in s_assessments:
            for label, val in _ldr_scores(a).items():
                if val is not None:
                    ldr_sums[label].append(val)
            for label, val in _ump_scores(a).items():
                if val is not None:
                    ump_sums[label].append(val)

        per_soldier.append({
            "id": s.id,
            "rank": s.rank,
            "name": s.name,
            "eval_count": len(s_assessments),
            "leader_averages": {k: round(sum(v)/len(v), 2) for k, v in ldr_sums.items() if v},
            "ump_averages":    {k: round(sum(v)/len(v), 2) for k, v in ump_sums.items() if v},
        })

    # Unit-level trend over time (group by event)
    event_buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for a in all_assessments:
        label = _event_label(a)
        for lbl, val in _ldr_scores(a).items():
            if val is not None:
                event_buckets[label][lbl].append(val)

    unit_trend = [
        {"event": ev, **{k: round(sum(v)/len(v), 2) for k, v in cats.items()}}
        for ev, cats in event_buckets.items()
    ]

    # ST&EO by mission across unit
    steo_buckets: dict[str, list[float]] = defaultdict(list)
    steo_assessments = [a for a in all_assessments if a.eval_category == "steo_eval"]
    for a in steo_assessments:
        ratings = db.query(DetailedRating).filter(DetailedRating.assessment_id == a.id).all()
        scores = [r.rating_score for r in ratings if r.rating_score]
        if scores and a.steo_mission_name:
            steo_buckets[a.steo_mission_name].append(sum(scores) / len(scores))

    steo_summary = [
        {
            "mission": mission,
            "avg_score": round(sum(vals) / len(vals), 2),
            "proficiency": _steo_proficiency(sum(vals) / len(vals)),
            "eval_count": len(vals),
        }
        for mission, vals in steo_buckets.items()
    ]

    return {
        "unit": unit,
        "soldier_count": len(soldiers),
        "eval_count": len(all_assessments),
        "per_soldier": per_soldier,
        "unit_trend": unit_trend,
        "steo_summary": steo_summary,
    }


# ---------------------------------------------------------------------------
# Battalion Performance Overview
# ---------------------------------------------------------------------------

@router.get("/battalion")
def battalion_overview(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    all_soldiers = db.query(Soldier).filter(Soldier.is_active == True).all()
    all_assessments = (
        db.query(Assessment)
        .order_by(Assessment.created_at.asc())
        .all()
    )

    # Group by unit
    units: dict[str, dict[str, Any]] = {}
    for s in all_soldiers:
        u = s.unit or "Unknown"
        if u not in units:
            units[u] = {"soldiers": [], "assessments": []}
        units[u]["soldiers"].append(s)

    for a in all_assessments:
        soldier = next((s for s in all_soldiers if s.id == a.soldier_id), None)
        if soldier:
            u = soldier.unit or "Unknown"
            if u in units:
                units[u]["assessments"].append(a)

    summary: list[dict] = []
    for unit_name, data in sorted(units.items()):
        ldr_sums: dict[str, list[float]] = defaultdict(list)
        ump_sums: dict[str, list[float]] = defaultdict(list)
        for a in data["assessments"]:
            for label, val in _ldr_scores(a).items():
                if val is not None:
                    ldr_sums[label].append(val)
            for label, val in _ump_scores(a).items():
                if val is not None:
                    ump_sums[label].append(val)

        summary.append({
            "unit": unit_name,
            "soldier_count": len(data["soldiers"]),
            "eval_count": len(data["assessments"]),
            "leader_averages": {k: round(sum(v)/len(v), 2) for k, v in ldr_sums.items() if v},
            "ump_averages":    {k: round(sum(v)/len(v), 2) for k, v in ump_sums.items() if v},
        })

    # Battalion-wide aggregated averages
    all_ldr: dict[str, list[float]] = defaultdict(list)
    all_ump: dict[str, list[float]] = defaultdict(list)
    for a in all_assessments:
        for label, val in _ldr_scores(a).items():
            if val is not None:
                all_ldr[label].append(val)
        for label, val in _ump_scores(a).items():
            if val is not None:
                all_ump[label].append(val)

    return {
        "total_soldiers": len(all_soldiers),
        "total_evals": len(all_assessments),
        "battalion_leader_avg": {k: round(sum(v)/len(v), 2) for k, v in all_ldr.items() if v},
        "battalion_ump_avg":    {k: round(sum(v)/len(v), 2) for k, v in all_ump.items() if v},
        "units": summary,
    }
