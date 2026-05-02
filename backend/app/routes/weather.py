from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import WeatherSnapshot
from backend.app.deps import get_current_user
from backend.app.db.models import User

router = APIRouter(prefix="/weather", tags=["Weather — ATAK Context"])


class WeatherCreate(BaseModel):
    mgrs_grid:      str
    temperature_c:  float | None = None
    humidity_pct:   float | None = None
    wind_speed_kmh: float | None = None
    visibility_km:  float = 10.0
    wbgt:           float | None = None   # Wet Bulb Globe Temperature
    precipitation:  str = "none"          # none / light / heavy


def _snap_dict(s: WeatherSnapshot) -> dict:
    return {
        "id":             s.id,
        "mgrs_grid":      s.mgrs_grid,
        "temperature_c":  s.temperature_c,
        "humidity_pct":   s.humidity_pct,
        "wind_speed_kmh": s.wind_speed_kmh,
        "visibility_km":  s.visibility_km,
        "wbgt":           s.wbgt,
        "precipitation":  s.precipitation,
        "recorded_at":    s.recorded_at.isoformat() if s.recorded_at else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_snapshot(
    body: WeatherCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    snap = WeatherSnapshot(**body.model_dump())
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return _snap_dict(snap)


@router.get("/latest")
def get_latest(
    grid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the most recent weather snapshot for an MGRS grid."""
    snap = (
        db.query(WeatherSnapshot)
        .filter(WeatherSnapshot.mgrs_grid == grid)
        .order_by(WeatherSnapshot.recorded_at.desc())
        .first()
    )
    if not snap:
        raise HTTPException(404, detail=f"No weather data for grid {grid}")
    return _snap_dict(snap)


@router.get("")
def list_snapshots(
    grid: str | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List recent weather snapshots, optionally filtered by MGRS grid."""
    q = db.query(WeatherSnapshot).order_by(WeatherSnapshot.recorded_at.desc())
    if grid:
        q = q.filter(WeatherSnapshot.mgrs_grid == grid)
    return [_snap_dict(s) for s in q.limit(limit).all()]


@router.delete("/{snapshot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    snap = db.query(WeatherSnapshot).filter(WeatherSnapshot.id == snapshot_id).first()
    if not snap:
        raise HTTPException(404, detail="Snapshot not found")
    db.delete(snap)
    db.commit()
