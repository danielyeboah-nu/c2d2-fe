from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Any

from backend.app.db.database import get_db
from backend.app.db.models import AdversarialSim, BattlespaceSession, RiskVector, SensorTrack, User
from backend.app.deps import get_current_user
from backend.app.services.adversarial_ai import run_adversarial_simulation

router = APIRouter(prefix="/battlespace", tags=["Battlespace — Phase 03"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SessionCreate(BaseModel):
    session_name: str
    mission_id: int | None = None
    scenario_description: str | None = None
    friendly_units: list[dict] = []
    known_enemy: list[dict] = []
    intel_reports: list[str] = []


class SessionUpdate(BaseModel):
    session_name: str | None = None
    scenario_description: str | None = None
    friendly_units: list[dict] | None = None
    known_enemy: list[dict] | None = None
    intel_reports: list[str] | None = None
    status: str | None = None


class SensorTrackCreate(BaseModel):
    track_type: str = "friendly"
    callsign: str
    grid: str | None = None
    heading_deg: int | None = None
    speed_kmh: float | None = None
    status: str | None = None


def _session_dict(s: BattlespaceSession, include_tracks: bool = False) -> dict:
    d = {
        "id": s.id,
        "session_name": s.session_name,
        "status": s.status,
        "mission_id": s.mission_id,
        "scenario_description": s.scenario_description,
        "friendly_units": s.friendly_units or [],
        "known_enemy": s.known_enemy or [],
        "intel_reports": s.intel_reports or [],
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }
    if include_tracks:
        d["sensor_tracks"] = [
            {
                "id": t.id, "track_type": t.track_type, "callsign": t.callsign,
                "grid": t.grid, "heading_deg": t.heading_deg, "speed_kmh": t.speed_kmh,
                "status": t.status, "reported_at": t.reported_at.isoformat() if t.reported_at else None,
            }
            for t in s.sensor_tracks
        ]
        d["risk_vectors"] = [
            {
                "id": rv.id, "risk_type": rv.risk_type, "severity": rv.severity,
                "description": rv.description, "affected_units": rv.affected_units or [],
                "recommended_action": rv.recommended_action,
                "confidence_score": rv.confidence_score, "ai_generated": rv.ai_generated,
                "created_at": rv.created_at.isoformat() if rv.created_at else None,
            }
            for rv in s.risk_vectors
        ]
    return d


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = db.query(BattlespaceSession).order_by(BattlespaceSession.created_at.desc()).all()
    return [_session_dict(s) for s in sessions]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_session(
    body: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = BattlespaceSession(**body.model_dump(), created_by_user_id=current_user.id)
    db.add(s)
    db.commit()
    db.refresh(s)
    return _session_dict(s)


@router.get("/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.query(BattlespaceSession).filter(BattlespaceSession.id == session_id).first()
    if not s:
        raise HTTPException(404, detail="Session not found")
    return _session_dict(s, include_tracks=True)


@router.patch("/{session_id}")
def update_session(
    session_id: int,
    body: SessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.query(BattlespaceSession).filter(BattlespaceSession.id == session_id).first()
    if not s:
        raise HTTPException(404, detail="Session not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(s, field, val)
    db.commit()
    db.refresh(s)
    return _session_dict(s)


@router.post("/{session_id}/sensor-tracks", status_code=status.HTTP_201_CREATED)
def add_sensor_track(
    session_id: int,
    body: SensorTrackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.query(BattlespaceSession).filter(BattlespaceSession.id == session_id).first()
    if not s:
        raise HTTPException(404, detail="Session not found")
    track = SensorTrack(session_id=session_id, **body.model_dump())
    db.add(track)
    db.commit()
    db.refresh(track)
    return {
        "id": track.id, "session_id": track.session_id,
        "track_type": track.track_type, "callsign": track.callsign,
        "grid": track.grid, "status": track.status,
    }


@router.post("/{session_id}/simulate-adversary")
def simulate_adversary(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Phase 03 — Run the adversarial AI simulation.
    Generates adversary moves, risk vectors, and recommended actions.
    """
    s = db.query(BattlespaceSession).filter(BattlespaceSession.id == session_id).first()
    if not s:
        raise HTTPException(404, detail="Session not found")
    if s.status == "closed":
        raise HTTPException(400, detail="Session is closed")

    # Determine next simulation round
    round_num = len(s.simulations) + 1

    # Build context dict including live sensor tracks
    tracks = [
        {"track_type": t.track_type, "callsign": t.callsign, "grid": t.grid, "status": t.status}
        for t in s.sensor_tracks
    ]

    session_dict = {
        "session_name": s.session_name,
        "scenario_description": s.scenario_description,
        "friendly_units": s.friendly_units or [],
        "known_enemy": s.known_enemy or [],
        "intel_reports": s.intel_reports or [],
        "sensor_tracks": tracks,
    }

    sim_result = run_adversarial_simulation(session_dict)

    # Persist simulation record
    sim = AdversarialSim(
        session_id=session_id,
        simulation_round=round_num,
        ai_model_used=sim_result.get("ai_model_used", "unknown"),
        adversary_moves=sim_result.get("adversary_moves", []),
        risk_vectors_generated=sim_result.get("risk_vectors", []),
        recommendations=sim_result.get("recommendations", []),
        raw_ai_response=str(sim_result),
    )
    db.add(sim)

    # Persist risk vectors
    for rv_data in sim_result.get("risk_vectors", []):
        rv = RiskVector(
            session_id=session_id,
            risk_type=rv_data.get("risk_type", "unknown"),
            severity=rv_data.get("severity", "medium"),
            description=rv_data.get("description", ""),
            affected_units=rv_data.get("affected_units", []),
            recommended_action=rv_data.get("recommended_action", ""),
            confidence_score=rv_data.get("confidence_score", 0.0),
            ai_generated=True,
        )
        db.add(rv)

    db.commit()
    return {
        "session_id": session_id,
        "simulation_round": round_num,
        "situation_summary": sim_result.get("situation_summary", ""),
        "adversary_moves": sim_result.get("adversary_moves", []),
        "risk_vectors": sim_result.get("risk_vectors", []),
        "recommendations": sim_result.get("recommendations", []),
    }


@router.get("/{session_id}/risk-vectors")
def get_risk_vectors(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.query(BattlespaceSession).filter(BattlespaceSession.id == session_id).first()
    if not s:
        raise HTTPException(404, detail="Session not found")
    return [
        {
            "id": rv.id, "risk_type": rv.risk_type, "severity": rv.severity,
            "description": rv.description, "affected_units": rv.affected_units or [],
            "recommended_action": rv.recommended_action,
            "confidence_score": rv.confidence_score,
            "created_at": rv.created_at.isoformat() if rv.created_at else None,
        }
        for rv in sorted(s.risk_vectors, key=lambda r: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(r.severity, 4))
    ]


@router.post("/{session_id}/close")
def close_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.query(BattlespaceSession).filter(BattlespaceSession.id == session_id).first()
    if not s:
        raise HTTPException(404, detail="Session not found")
    s.status = "closed"
    db.commit()
    return {"session_id": session_id, "status": "closed"}
