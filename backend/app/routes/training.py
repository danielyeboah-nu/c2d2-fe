from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import Soldier, TrainingSchedule, TrainingSlot, User
from backend.app.deps import get_current_user
from backend.app.services.schedule_generator import MISSIONS, ROLES, generate_schedule, lead_summary

router = APIRouter(prefix="/training-schedules", tags=["Training Schedule — Phase 02"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ScheduleCreate(BaseModel):
    name: str
    platoon_name: str | None = None
    num_days: int = 10
    start_date: str | None = None    # "YYYY-MM-DD"
    soldier_ids: list[int]


class SlotUpdate(BaseModel):
    soldier_id: int | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slot_dict(slot: TrainingSlot) -> dict:
    s = slot.soldier
    return {
        "id":           slot.id,
        "day_number":   slot.day_number,
        "mission_type": slot.mission_type,
        "role":         slot.role,
        "soldier_id":   slot.soldier_id,
        "soldier_name": f"{s.rank} {s.name}" if s else None,
    }


def _schedule_dict(sched: TrainingSchedule, include_slots: bool = False) -> dict:
    d = {
        "id":           sched.id,
        "name":         sched.name,
        "platoon_name": sched.platoon_name,
        "num_days":     sched.num_days,
        "start_date":   sched.start_date,
        "slot_count":   len(sched.slots),
        "created_at":   sched.created_at.isoformat() if sched.created_at else None,
    }
    if include_slots:
        d["slots"] = [_slot_dict(sl) for sl in sched.slots]
    return d


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
def list_schedules(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    scheds = db.query(TrainingSchedule).order_by(TrainingSchedule.created_at.desc()).all()
    return [_schedule_dict(s) for s in scheds]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_schedule(
    body: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new training schedule and auto-generate the rotation.

    Pass a list of soldier IDs (up to 32) and the server will produce
    a balanced 10-day assignment grid.
    """
    soldiers = db.query(Soldier).filter(Soldier.id.in_(body.soldier_ids)).all()
    if not soldiers:
        raise HTTPException(400, detail="No valid soldiers found for the given IDs")

    soldier_dicts = [
        {
            "id":                    s.id,
            "rank":                  s.rank,
            "name":                  s.name,
            "skill_leadership":      s.skill_leadership or 0.5,
            "skill_decision_making": s.skill_decision_making or 0.5,
            "skill_stress_tolerance":s.skill_stress_tolerance or 0.5,
            "skill_tactical":        s.skill_tactical or 0.5,
            "skill_communication":   s.skill_communication or 0.5,
            "skill_teamwork":        s.skill_teamwork or 0.5,
            "skill_adaptability":    s.skill_adaptability or 0.5,
            "skill_physical":        s.skill_physical or 0.5,
            "skill_technical":       s.skill_technical or 0.5,
        }
        for s in soldiers
    ]

    sched = TrainingSchedule(
        name=body.name,
        platoon_name=body.platoon_name,
        num_days=body.num_days,
        start_date=body.start_date,
        created_by_user_id=current_user.id,
    )
    db.add(sched)
    db.flush()

    raw_slots = generate_schedule(soldier_dicts, num_days=body.num_days)
    for s in raw_slots:
        db.add(TrainingSlot(
            schedule_id=sched.id,
            day_number=s["day_number"],
            mission_type=s["mission_type"],
            role=s["role"],
            soldier_id=s["soldier_id"],
        ))

    db.commit()
    db.refresh(sched)
    return _schedule_dict(sched, include_slots=True)


@router.get("/{schedule_id}")
def get_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    sched = db.query(TrainingSchedule).filter(TrainingSchedule.id == schedule_id).first()
    if not sched:
        raise HTTPException(404, detail="Schedule not found")
    return _schedule_dict(sched, include_slots=True)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    sched = db.query(TrainingSchedule).filter(TrainingSchedule.id == schedule_id).first()
    if not sched:
        raise HTTPException(404, detail="Schedule not found")
    db.delete(sched)
    db.commit()


@router.patch("/{schedule_id}/slots/{slot_id}")
def update_slot(
    schedule_id: int,
    slot_id: int,
    body: SlotUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Swap the soldier assigned to a single slot (manual override)."""
    slot = db.query(TrainingSlot).filter(
        TrainingSlot.id == slot_id,
        TrainingSlot.schedule_id == schedule_id,
    ).first()
    if not slot:
        raise HTTPException(404, detail="Slot not found")

    slot.soldier_id = body.soldier_id
    db.commit()
    db.refresh(slot)
    return _slot_dict(slot)


@router.get("/{schedule_id}/progress")
def get_progress(
    schedule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return per-soldier leadership counts and role breakdown."""
    sched = db.query(TrainingSchedule).filter(TrainingSchedule.id == schedule_id).first()
    if not sched:
        raise HTTPException(404, detail="Schedule not found")

    # Collect all soldier IDs referenced in this schedule
    soldier_ids = list({sl.soldier_id for sl in sched.slots if sl.soldier_id is not None})
    soldiers = db.query(Soldier).filter(Soldier.id.in_(soldier_ids)).all()
    soldier_dicts = [{"id": s.id, "rank": s.rank, "name": s.name} for s in soldiers]

    raw_slots = [
        {"day_number": sl.day_number, "mission_type": sl.mission_type,
         "role": sl.role, "soldier_id": sl.soldier_id}
        for sl in sched.slots
    ]

    summary = lead_summary(raw_slots, soldier_dicts)
    return {
        "schedule_id": schedule_id,
        "missions":    MISSIONS,
        "roles":       ROLES,
        "soldiers":    summary,
    }
