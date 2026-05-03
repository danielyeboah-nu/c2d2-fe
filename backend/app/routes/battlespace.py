from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Any

from backend.app.db.database import get_db, get_session_factory
from backend.app.db.models import (
    AdversarialSim, BattlespaceSession, Mission, RiskVector, SimulationJob,
    Soldier, SoldierReadiness, SensorTrack, TeamComposition, User, WeatherSnapshot,
)
from backend.app.deps import get_current_user
from backend.app.services.adversarial_ai import run_adversarial_simulation

router = APIRouter(prefix="/battlespace", tags=["Battlespace — Phase 03"])

logger = logging.getLogger(__name__)


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
# Background task
# ---------------------------------------------------------------------------

def _run_sim_background(job_id: int, session_dict: dict) -> None:
    """Executes the adversarial simulation in a background thread."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
        if not job:
            return

        job.status = "running"
        db.commit()

        result = run_adversarial_simulation(session_dict)

        sim = AdversarialSim(
            session_id=job.session_id,
            simulation_round=job.sim_round,
            ai_model_used=result.get("ai_model_used", "unknown"),
            adversary_moves=result.get("adversary_moves", []),
            risk_vectors_generated=result.get("risk_vectors", []),
            recommendations=result.get("recommendations", []),
            raw_ai_response=str(result),
        )
        db.add(sim)

        for rv_data in result.get("risk_vectors", []):
            rv = RiskVector(
                session_id=job.session_id,
                risk_type=rv_data.get("risk_type", "unknown"),
                severity=rv_data.get("severity", "medium"),
                description=rv_data.get("description", ""),
                affected_units=rv_data.get("affected_units", []),
                recommended_action=rv_data.get("recommended_action", ""),
                confidence_score=rv_data.get("confidence_score", 0.0),
                ai_generated=True,
            )
            db.add(rv)

        job.status = "completed"
        job.result = result
        job.ai_model_used = result.get("ai_model_used")
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as exc:
        logger.error("Simulation job %d failed: %s", job_id, exc)
        try:
            db.rollback()
            job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.error = str(exc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


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


# NOTE: /jobs/{job_id} must be defined before /{session_id} to avoid param collision
@router.get("/jobs/{job_id}")
def get_sim_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
    if not job:
        raise HTTPException(404, detail="Job not found")
    return {
        "job_id": job.id,
        "session_id": job.session_id,
        "sim_round": job.sim_round,
        "status": job.status,
        "result": job.result,
        "error": job.error,
        "ai_model_used": job.ai_model_used,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Phase 03 — Queue an adversarial AI simulation as a background job.
    Returns a job_id immediately; poll GET /jobs/{job_id} for status and results.
    """
    s = db.query(BattlespaceSession).filter(BattlespaceSession.id == session_id).first()
    if not s:
        raise HTTPException(404, detail="Session not found")
    if s.status == "closed":
        raise HTTPException(400, detail="Session is closed")

    # Block if a job is already running for this session
    active_job = (
        db.query(SimulationJob)
        .filter(
            SimulationJob.session_id == session_id,
            SimulationJob.status.in_(["pending", "running"]),
        )
        .first()
    )
    if active_job:
        return {"job_id": active_job.id, "status": active_job.status, "session_id": session_id}

    round_num = len(s.simulations) + 1

    # Live sensor tracks
    tracks = [
        {"track_type": t.track_type, "callsign": t.callsign, "grid": t.grid, "status": t.status}
        for t in s.sensor_tracks
    ]

    # Enrich with squad composition + mission context when session is linked to a mission
    squad_members: list[dict] = []
    mission_context: dict | None = None

    if s.mission_id:
        mission = db.query(Mission).filter(Mission.id == s.mission_id).first()
        if mission:
            mission_context = {
                "mission_name":    mission.mission_name,
                "mission_type":    mission.mission_type,
                "threat_level":    mission.threat_level,
                "terrain_type":    mission.terrain_type,
                "duration_hours":  mission.duration_hours,
                "ao_grid_center":  mission.ao_grid_center,
            }

            if mission.ao_grid_center:
                snap = (
                    db.query(WeatherSnapshot)
                    .filter(WeatherSnapshot.mgrs_grid == mission.ao_grid_center)
                    .order_by(WeatherSnapshot.recorded_at.desc())
                    .first()
                )
                if snap:
                    mission_context["weather"] = {
                        "temperature_c":  snap.temperature_c,
                        "humidity_pct":   snap.humidity_pct,
                        "wind_speed_kmh": snap.wind_speed_kmh,
                        "visibility_km":  snap.visibility_km,
                        "wbgt":           snap.wbgt,
                        "precipitation":  snap.precipitation,
                    }

            comp: TeamComposition | None = None
            if mission.selected_composition_id:
                comp = db.query(TeamComposition).filter(
                    TeamComposition.id == mission.selected_composition_id
                ).first()
            if comp is None and mission.compositions:
                comp = sorted(mission.compositions, key=lambda c: c.composition_rank)[0]

            if comp:
                readiness_by_soldier: dict[int, SoldierReadiness] = {
                    r.soldier_id: r
                    for r in db.query(SoldierReadiness).all()
                }
                for member in comp.members:
                    sol: Soldier | None = member.soldier
                    if not sol:
                        continue
                    rd = readiness_by_soldier.get(sol.id)
                    squad_members.append({
                        "name":          f"{sol.rank} {sol.name}",
                        "role":          member.role or "rifleman",
                        "fit_score":     round(member.fit_score, 3),
                        "fit_notes":     member.fit_notes,
                        "skills": {
                            "leadership":      round(sol.skill_leadership or 0.5, 2),
                            "decision_making": round(sol.skill_decision_making or 0.5, 2),
                            "stress_tolerance":round(sol.skill_stress_tolerance or 0.5, 2),
                            "tactical":        round(sol.skill_tactical or 0.5, 2),
                            "communication":   round(sol.skill_communication or 0.5, 2),
                            "teamwork":        round(sol.skill_teamwork or 0.5, 2),
                            "adaptability":    round(sol.skill_adaptability or 0.5, 2),
                            "physical":        round(sol.skill_physical or 0.5, 2),
                            "technical":       round(sol.skill_technical or 0.5, 2),
                        },
                        "fatigue_index":   round(rd.fatigue_index, 3) if rd else None,
                        "injury_status":   rd.injury_status if rd else "unknown",
                        "sleep_hours_24h": rd.sleep_hours_24h if rd else None,
                        "sleep_hours_48h": rd.sleep_hours_48h if rd else None,
                    })

    session_dict = {
        "session_name":        s.session_name,
        "scenario_description":s.scenario_description,
        "friendly_units":      s.friendly_units or [],
        "known_enemy":         s.known_enemy or [],
        "intel_reports":       s.intel_reports or [],
        "sensor_tracks":       tracks,
        "squad_members":       squad_members,
        "mission_context":     mission_context,
    }

    job = SimulationJob(session_id=session_id, sim_round=round_num, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_run_sim_background, job.id, session_dict)

    return {"job_id": job.id, "status": "pending", "session_id": session_id}


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
