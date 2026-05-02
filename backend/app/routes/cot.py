"""
CoT ingest endpoint — used by the ATAK plugin to POST position/readiness
directly to the backend without going through TAK Server.

POST /api/v1/cot/position   — raw CoT XML body or JSON position
POST /api/v1/cot/readiness  — JSON readiness update from plugin
POST /api/v1/cot/link       — link a TAK UID to a soldier ID
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import Soldier, SoldierPosition, SoldierReadiness
from backend.app.deps import get_current_user
from backend.app.db.models import User
from backend.app.services.cot_parser import parse_cot
from backend.app.routes.soldiers import _readiness_dict, _position_dict, _fatigue_index

router = APIRouter(prefix="/cot", tags=["ATAK CoT Ingest"])


class PositionPayload(BaseModel):
    tak_uid:            str
    lat:                float
    lon:                float
    mgrs_grid:          str | None = None
    operational_status: str = "available"


class ReadinessPayload(BaseModel):
    tak_uid:         str
    sleep_hours_24h: float
    sleep_hours_48h: float = 16.0
    injury_status:   str   = "fit"


class LinkPayload(BaseModel):
    soldier_id: int
    tak_uid:    str


def _resolve_soldier(tak_uid: str, db: Session) -> Soldier | None:
    """Find soldier by tak_uid; falls back to callsign substring match."""
    return db.query(Soldier).filter(Soldier.tak_uid == tak_uid).first()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/position")
def ingest_position(
    body: PositionPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Direct JSON position update from the ATAK plugin."""
    soldier = _resolve_soldier(body.tak_uid, db)
    if not soldier:
        raise HTTPException(404, detail=f"No soldier linked to TAK UID {body.tak_uid!r}. Use /cot/link first.")

    pos = db.query(SoldierPosition).filter(SoldierPosition.soldier_id == soldier.id).first()
    if pos:
        pos.lat                = body.lat
        pos.lon                = body.lon
        if body.mgrs_grid:
            pos.mgrs_grid      = body.mgrs_grid
        pos.operational_status = body.operational_status
    else:
        pos = SoldierPosition(
            soldier_id=soldier.id,
            lat=body.lat,
            lon=body.lon,
            mgrs_grid=body.mgrs_grid,
            operational_status=body.operational_status,
        )
        db.add(pos)

    db.commit()
    db.refresh(pos)
    return _position_dict(pos)


@router.post("/position/raw")
async def ingest_cot_xml(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accept raw CoT XML body (Content-Type: application/xml) from the plugin."""
    body = await request.body()
    cot  = parse_cot(body.decode("utf-8", errors="ignore"))
    if not cot:
        raise HTTPException(400, detail="Could not parse CoT XML")

    soldier = (
        db.query(Soldier).filter(Soldier.tak_uid == cot.uid).first()
        or db.query(Soldier).filter(
            Soldier.is_active == True,
            Soldier.name.ilike(f"%{cot.callsign}%"),
        ).first()
    )
    if not soldier:
        raise HTTPException(404, detail=f"No soldier matched uid={cot.uid!r} callsign={cot.callsign!r}")

    pos = db.query(SoldierPosition).filter(SoldierPosition.soldier_id == soldier.id).first()
    if pos:
        pos.lat = cot.lat
        pos.lon = cot.lon
    else:
        pos = SoldierPosition(soldier_id=soldier.id, lat=cot.lat, lon=cot.lon, operational_status="available")
        db.add(pos)

    db.commit()
    db.refresh(pos)
    return {"soldier_id": soldier.id, "name": soldier.name, **_position_dict(pos)}


@router.post("/readiness")
def ingest_readiness(
    body: ReadinessPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Readiness update (sleep/injury) from the ATAK plugin."""
    soldier = _resolve_soldier(body.tak_uid, db)
    if not soldier:
        raise HTTPException(404, detail=f"No soldier linked to TAK UID {body.tak_uid!r}")

    r = db.query(SoldierReadiness).filter(SoldierReadiness.soldier_id == soldier.id).first()
    if r:
        r.sleep_hours_24h = body.sleep_hours_24h
        r.sleep_hours_48h = body.sleep_hours_48h
        r.fatigue_index   = _fatigue_index(body.sleep_hours_24h, body.sleep_hours_48h)
        r.injury_status   = body.injury_status
    else:
        r = SoldierReadiness(
            soldier_id=soldier.id,
            sleep_hours_24h=body.sleep_hours_24h,
            sleep_hours_48h=body.sleep_hours_48h,
            fatigue_index=_fatigue_index(body.sleep_hours_24h, body.sleep_hours_48h),
            injury_status=body.injury_status,
        )
        db.add(r)

    db.commit()
    db.refresh(r)
    return {"soldier_id": soldier.id, "name": soldier.name, **_readiness_dict(r)}


@router.post("/link", status_code=status.HTTP_200_OK)
def link_tak_uid(
    body: LinkPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    One-time pairing: associate an ATAK device UID with a soldier record.
    Called once when the soldier opens the plugin for the first time.
    """
    soldier = db.query(Soldier).filter(Soldier.id == body.soldier_id).first()
    if not soldier:
        raise HTTPException(404, detail="Soldier not found")

    # Unlink any previously linked soldier with this UID
    existing = db.query(Soldier).filter(Soldier.tak_uid == body.tak_uid).first()
    if existing and existing.id != soldier.id:
        existing.tak_uid = None

    soldier.tak_uid = body.tak_uid
    db.commit()
    return {"soldier_id": soldier.id, "name": soldier.name, "tak_uid": soldier.tak_uid}
