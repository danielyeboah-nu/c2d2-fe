from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import TrainingEvent, User
from backend.app.deps import get_current_user

router = APIRouter(prefix="/events", tags=["Training Events"])


class EventCreate(BaseModel):
    event_name: str
    event_type: str = "FTX"
    event_date: str | None = None
    location: str | None = None
    mission_type: str | None = None
    notes: str | None = None


def _event_dict(e: TrainingEvent) -> dict:
    return {
        "id": e.id,
        "event_name": e.event_name,
        "event_type": e.event_type,
        "event_date": e.event_date,
        "location": e.location,
        "mission_type": e.mission_type,
        "notes": e.notes,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("")
def list_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return [_event_dict(e) for e in db.query(TrainingEvent).order_by(TrainingEvent.event_date.desc()).all()]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_event(
    body: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    e = TrainingEvent(**body.model_dump(), owner_user_id=current_user.id, created_by_user_id=current_user.id)
    db.add(e)
    db.commit()
    db.refresh(e)
    return _event_dict(e)


@router.get("/{event_id}")
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    e = db.query(TrainingEvent).filter(TrainingEvent.id == event_id).first()
    if not e:
        raise HTTPException(404, detail="Event not found")
    return _event_dict(e)


@router.patch("/{event_id}")
def update_event(
    event_id: int,
    body: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    e = db.query(TrainingEvent).filter(TrainingEvent.id == event_id).first()
    if not e:
        raise HTTPException(404, detail="Event not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(e, field, val)
    db.commit()
    db.refresh(e)
    return _event_dict(e)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    e = db.query(TrainingEvent).filter(TrainingEvent.id == event_id).first()
    if not e:
        raise HTTPException(404, detail="Event not found")
    db.delete(e)
    db.commit()
