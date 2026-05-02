from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Any

from backend.app.db.database import get_db
from backend.app.db.models import Assessment, Soldier, SoldierReadiness, SoldierPosition
from backend.app.deps import get_current_user
from backend.app.db.models import User

router = APIRouter(prefix="/soldiers", tags=["Soldiers"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class SoldierCreate(BaseModel):
    service_number: str
    rank: str
    name: str
    unit: str | None = None
    mos: str | None = None
    leader_type: str | None = None
    decision_style: str = "methodical"
    leadership_traits: list[str] = []
    skill_leadership: float = 0.5
    skill_decision_making: float = 0.5
    skill_stress_tolerance: float = 0.5
    skill_tactical: float = 0.5
    skill_communication: float = 0.5
    skill_teamwork: float = 0.5
    skill_adaptability: float = 0.5
    skill_physical: float = 0.5
    skill_technical: float = 0.5


class ReadinessUpsert(BaseModel):
    sleep_hours_24h: float
    sleep_hours_48h: float = 16.0
    injury_status: str = "fit"   # fit / light_duty / unfit


class PositionUpsert(BaseModel):
    mgrs_grid: str | None = None
    lat: float | None = None
    lon: float | None = None
    operational_status: str = "available"  # available / on_mission / casualty / rest


class SoldierUpdate(BaseModel):
    rank: str | None = None
    name: str | None = None
    unit: str | None = None
    mos: str | None = None
    leader_type: str | None = None
    decision_style: str | None = None
    leadership_traits: list[str] | None = None
    is_active: bool | None = None
    skill_leadership: float | None = None
    skill_decision_making: float | None = None
    skill_stress_tolerance: float | None = None
    skill_tactical: float | None = None
    skill_communication: float | None = None
    skill_teamwork: float | None = None
    skill_adaptability: float | None = None
    skill_physical: float | None = None
    skill_technical: float | None = None


def _soldier_dict(s: Soldier) -> dict:
    return {
        "id": s.id,
        "service_number": s.service_number,
        "rank": s.rank,
        "name": s.name,
        "unit": s.unit,
        "mos": s.mos,
        "leader_type": s.leader_type,
        "is_active": s.is_active,
        "decision_style": s.decision_style,
        "leadership_traits": s.leadership_traits or [],
        "skill_vector": {
            "leadership": s.skill_leadership,
            "decision_making": s.skill_decision_making,
            "stress_tolerance": s.skill_stress_tolerance,
            "tactical": s.skill_tactical,
            "communication": s.skill_communication,
            "teamwork": s.skill_teamwork,
            "adaptability": s.skill_adaptability,
            "physical": s.skill_physical,
            "technical": s.skill_technical,
        },
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/force-status")
def get_force_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Combined force readiness snapshot: all active soldiers with positions and readiness data."""
    soldiers     = db.query(Soldier).filter(Soldier.is_active == True).all()
    readiness_map = {r.soldier_id: r for r in db.query(SoldierReadiness).all()}
    position_map  = {p.soldier_id: p for p in db.query(SoldierPosition).all()}
    active_ids    = {s.id for s in soldiers}

    rows = []
    for s in soldiers:
        rows.append({
            "id":       s.id,
            "rank":     s.rank,
            "name":     s.name,
            "unit":     s.unit,
            "readiness": _readiness_dict(readiness_map[s.id]) if s.id in readiness_map else None,
            "position":  _position_dict(position_map[s.id])   if s.id in position_map  else None,
        })

    statuses = [position_map[sid].operational_status for sid in active_ids if sid in position_map]
    return {
        "soldiers": rows,
        "kpis": {
            "total":      len(soldiers),
            "available":  statuses.count("available"),
            "on_mission": statuses.count("on_mission"),
            "casualty":   statuses.count("casualty"),
            "rest":       statuses.count("rest"),
            "no_data":    len(soldiers) - len(statuses),
        },
    }


@router.get("")
def list_soldiers(
    active_only: bool = True,
    unit: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Soldier)
    if active_only:
        q = q.filter(Soldier.is_active == True)
    if unit:
        q = q.filter(Soldier.unit == unit)
    return [_soldier_dict(s) for s in q.all()]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_soldier(
    body: SoldierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.query(Soldier).filter(Soldier.service_number == body.service_number).first():
        raise HTTPException(400, detail="Service number already exists")

    s = Soldier(
        **{k: v for k, v in body.model_dump().items()},
        owner_user_id=current_user.id,
        created_by_user_id=current_user.id,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _soldier_dict(s)


@router.get("/{soldier_id}")
def get_soldier(
    soldier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.query(Soldier).filter(Soldier.id == soldier_id).first()
    if not s:
        raise HTTPException(404, detail="Soldier not found")
    return _soldier_dict(s)


@router.patch("/{soldier_id}")
def update_soldier(
    soldier_id: int,
    body: SoldierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.query(Soldier).filter(Soldier.id == soldier_id).first()
    if not s:
        raise HTTPException(404, detail="Soldier not found")

    for field, val in body.model_dump(exclude_none=True).items():
        setattr(s, field, val)
    db.commit()
    db.refresh(s)
    return _soldier_dict(s)


@router.delete("/{soldier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_soldier(
    soldier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.query(Soldier).filter(Soldier.id == soldier_id).first()
    if not s:
        raise HTTPException(404, detail="Soldier not found")
    db.delete(s)
    db.commit()


def _fatigue_index(sleep_24h: float, sleep_48h: float) -> float:
    """0.0 = fully rested, 1.0 = severely fatigued. Weighted deficit model."""
    deficit_24h = max(0.0, 8.0 - sleep_24h) / 8.0
    deficit_48h = max(0.0, 16.0 - sleep_48h) / 16.0
    return round(0.7 * deficit_24h + 0.3 * deficit_48h, 3)


def _readiness_dict(r: SoldierReadiness) -> dict:
    return {
        "soldier_id":      r.soldier_id,
        "sleep_hours_24h": r.sleep_hours_24h,
        "sleep_hours_48h": r.sleep_hours_48h,
        "fatigue_index":   r.fatigue_index,
        "injury_status":   r.injury_status,
        "updated_at":      r.updated_at.isoformat() if r.updated_at else None,
    }


def _position_dict(p: SoldierPosition) -> dict:
    return {
        "soldier_id":         p.soldier_id,
        "mgrs_grid":          p.mgrs_grid,
        "lat":                p.lat,
        "lon":                p.lon,
        "operational_status": p.operational_status,
        "updated_at":         p.updated_at.isoformat() if p.updated_at else None,
    }


@router.post("/{soldier_id}/readiness", status_code=status.HTTP_200_OK)
def upsert_readiness(
    soldier_id: int,
    body: ReadinessUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.query(Soldier).filter(Soldier.id == soldier_id).first()
    if not s:
        raise HTTPException(404, detail="Soldier not found")

    r = db.query(SoldierReadiness).filter(SoldierReadiness.soldier_id == soldier_id).first()
    if r:
        r.sleep_hours_24h = body.sleep_hours_24h
        r.sleep_hours_48h = body.sleep_hours_48h
        r.fatigue_index   = _fatigue_index(body.sleep_hours_24h, body.sleep_hours_48h)
        r.injury_status   = body.injury_status
    else:
        r = SoldierReadiness(
            soldier_id=soldier_id,
            sleep_hours_24h=body.sleep_hours_24h,
            sleep_hours_48h=body.sleep_hours_48h,
            fatigue_index=_fatigue_index(body.sleep_hours_24h, body.sleep_hours_48h),
            injury_status=body.injury_status,
        )
        db.add(r)

    db.commit()
    db.refresh(r)
    return _readiness_dict(r)


@router.get("/{soldier_id}/readiness")
def get_readiness(
    soldier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.query(Soldier).filter(Soldier.id == soldier_id).first()
    if not s:
        raise HTTPException(404, detail="Soldier not found")
    r = db.query(SoldierReadiness).filter(SoldierReadiness.soldier_id == soldier_id).first()
    if not r:
        raise HTTPException(404, detail="No readiness record for this soldier")
    return _readiness_dict(r)


@router.post("/{soldier_id}/position", status_code=status.HTTP_200_OK)
def upsert_position(
    soldier_id: int,
    body: PositionUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.query(Soldier).filter(Soldier.id == soldier_id).first()
    if not s:
        raise HTTPException(404, detail="Soldier not found")

    p = db.query(SoldierPosition).filter(SoldierPosition.soldier_id == soldier_id).first()
    if p:
        p.mgrs_grid          = body.mgrs_grid
        p.lat                = body.lat
        p.lon                = body.lon
        p.operational_status = body.operational_status
    else:
        p = SoldierPosition(
            soldier_id=soldier_id,
            mgrs_grid=body.mgrs_grid,
            lat=body.lat,
            lon=body.lon,
            operational_status=body.operational_status,
        )
        db.add(p)

    db.commit()
    db.refresh(p)
    return _position_dict(p)


@router.get("/{soldier_id}/position")
def get_position(
    soldier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.query(Soldier).filter(Soldier.id == soldier_id).first()
    if not s:
        raise HTTPException(404, detail="Soldier not found")
    p = db.query(SoldierPosition).filter(SoldierPosition.soldier_id == soldier_id).first()
    if not p:
        raise HTTPException(404, detail="No position record for this soldier")
    return _position_dict(p)


@router.get("/{soldier_id}/assessments")
def get_soldier_assessments(
    soldier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.query(Soldier).filter(Soldier.id == soldier_id).first()
    if not s:
        raise HTTPException(404, detail="Soldier not found")

    assessments = (
        db.query(Assessment)
        .filter(Assessment.soldier_id == soldier_id)
        .order_by(Assessment.created_at.desc())
        .all()
    )
    return [
        {
            "id": a.id,
            "event_id": a.event_id,
            "assessment_type": a.assessment_type,
            "capture_method": a.capture_method,
            "ai_analyzed": a.ai_analyzed,
            "ai_summary": a.ai_summary,
            "score_leadership": a.score_leadership,
            "score_decision_quality": a.score_decision_quality,
            "score_stress_response": a.score_stress_response,
            "score_tactical": a.score_tactical,
            "score_communication": a.score_communication,
            "notes": a.notes,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in assessments
    ]
