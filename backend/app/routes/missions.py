from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import Mission, Soldier, TeamComposition, TeamMember, User
from backend.app.deps import get_current_user
from backend.app.services.team_optimizer import optimize_team

router = APIRouter(prefix="/missions", tags=["Missions & Team Optimization — Phase 02"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MissionCreate(BaseModel):
    mission_name: str
    mission_type: str = "attack"
    threat_level: str = "medium"
    terrain_type: str = "general"
    required_team_size: int = 9
    special_requirements: list[str] = []
    duration_hours: float = 24.0
    description: str | None = None


class MissionUpdate(BaseModel):
    mission_name: str | None = None
    mission_type: str | None = None
    threat_level: str | None = None
    terrain_type: str | None = None
    required_team_size: int | None = None
    special_requirements: list[str] | None = None
    duration_hours: float | None = None
    description: str | None = None
    status: str | None = None


def _mission_dict(m: Mission, include_compositions: bool = False) -> dict:
    d = {
        "id": m.id,
        "mission_name": m.mission_name,
        "mission_type": m.mission_type,
        "threat_level": m.threat_level,
        "terrain_type": m.terrain_type,
        "required_team_size": m.required_team_size,
        "special_requirements": m.special_requirements or [],
        "duration_hours": m.duration_hours,
        "description": m.description,
        "status": m.status,
        "selected_composition_id": m.selected_composition_id,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }
    if include_compositions:
        d["compositions"] = [_composition_dict(c) for c in m.compositions]
    return d


def _composition_dict(c: TeamComposition) -> dict:
    return {
        "id": c.id,
        "mission_id": c.mission_id,
        "composition_rank": c.composition_rank,
        "team_size": c.team_size,
        "fit_score": c.fit_score,
        "rationale": c.rationale,
        "is_selected": c.is_selected,
        "members": [
            {
                "id": m.id,
                "soldier_id": m.soldier_id,
                "role": m.role,
                "fit_score": m.fit_score,
                "fit_notes": m.fit_notes,
                "name": f"{m.soldier.rank} {m.soldier.name}" if m.soldier else str(m.soldier_id),
                "unit": m.soldier.unit if m.soldier else None,
            }
            for m in c.members
        ],
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
def list_missions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return [_mission_dict(m) for m in db.query(Mission).order_by(Mission.created_at.desc()).all()]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_mission(
    body: MissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    m = Mission(**body.model_dump(), created_by_user_id=current_user.id)
    db.add(m)
    db.commit()
    db.refresh(m)
    return _mission_dict(m)


@router.get("/{mission_id}")
def get_mission(
    mission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    m = db.query(Mission).filter(Mission.id == mission_id).first()
    if not m:
        raise HTTPException(404, detail="Mission not found")
    return _mission_dict(m, include_compositions=True)


@router.patch("/{mission_id}")
def update_mission(
    mission_id: int,
    body: MissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    m = db.query(Mission).filter(Mission.id == mission_id).first()
    if not m:
        raise HTTPException(404, detail="Mission not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(m, field, val)
    db.commit()
    db.refresh(m)
    return _mission_dict(m)


@router.delete("/{mission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mission(
    mission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    m = db.query(Mission).filter(Mission.id == mission_id).first()
    if not m:
        raise HTTPException(404, detail="Mission not found")
    db.delete(m)
    db.commit()


@router.post("/{mission_id}/optimize-team")
def optimize_mission_team(
    mission_id: int,
    n_options: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Phase 02 — Run the team optimization engine.
    Scores all active soldiers for mission fit, generates up to 3 ranked team compositions.
    """
    m = db.query(Mission).filter(Mission.id == mission_id).first()
    if not m:
        raise HTTPException(404, detail="Mission not found")

    # Delete existing compositions for this mission
    for old in m.compositions:
        db.delete(old)
    db.flush()

    soldiers = db.query(Soldier).filter(Soldier.is_active == True).all()
    if len(soldiers) < m.required_team_size:
        raise HTTPException(400, detail=f"Not enough active soldiers ({len(soldiers)}) for team size {m.required_team_size}")

    soldier_dicts = [
        {
            "id": s.id, "rank": s.rank, "name": s.name, "unit": s.unit, "mos": s.mos,
            "leader_type": s.leader_type, "is_active": s.is_active,
            "skill_leadership": s.skill_leadership,
            "skill_decision_making": s.skill_decision_making,
            "skill_stress_tolerance": s.skill_stress_tolerance,
            "skill_tactical": s.skill_tactical,
            "skill_communication": s.skill_communication,
            "skill_teamwork": s.skill_teamwork,
            "skill_adaptability": s.skill_adaptability,
            "leadership_traits": s.leadership_traits or [],
            "qualifications": s.personality_profile.get("qualifications", []) if s.personality_profile else [],
        }
        for s in soldiers
    ]

    mission_dict = {
        "mission_name": m.mission_name,
        "mission_type": m.mission_type,
        "threat_level": m.threat_level,
        "terrain_type": m.terrain_type,
        "required_team_size": m.required_team_size,
        "special_requirements": m.special_requirements or [],
    }

    compositions = optimize_team(mission_dict, soldier_dicts, n_options=n_options)

    saved = []
    for comp_data in compositions:
        comp = TeamComposition(
            mission_id=mission_id,
            composition_rank=comp_data["composition_rank"],
            team_size=comp_data["team_size"],
            fit_score=comp_data["fit_score"],
            rationale=comp_data["rationale"],
        )
        db.add(comp)
        db.flush()

        for member_data in comp_data["members"]:
            member = TeamMember(
                composition_id=comp.id,
                soldier_id=member_data["soldier_id"],
                role=member_data.get("role", "rifleman"),
                fit_score=member_data.get("fit_score", 0.0),
            )
            db.add(member)

        db.flush()
        db.refresh(comp)
        saved.append(_composition_dict(comp))

    db.commit()
    return {"mission_id": mission_id, "compositions": saved}


@router.get("/{mission_id}/team-options")
def get_team_options(
    mission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    m = db.query(Mission).filter(Mission.id == mission_id).first()
    if not m:
        raise HTTPException(404, detail="Mission not found")
    return [_composition_dict(c) for c in sorted(m.compositions, key=lambda c: c.composition_rank)]


@router.post("/{mission_id}/select-team/{composition_id}")
def select_team(
    mission_id: int,
    composition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Commander selects a team composition — final authority."""
    m = db.query(Mission).filter(Mission.id == mission_id).first()
    if not m:
        raise HTTPException(404, detail="Mission not found")

    for comp in m.compositions:
        comp.is_selected = comp.id == composition_id

    m.selected_composition_id = composition_id
    m.status = "active"
    db.commit()
    return {"selected": composition_id, "mission_status": m.status}
