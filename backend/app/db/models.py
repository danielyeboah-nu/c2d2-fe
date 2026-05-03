from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
)
from sqlalchemy.orm import relationship

from backend.app.db.database import Base


def _now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name     = Column(String(255))
    role          = Column(String(50), nullable=False, default="evaluator")
    unit          = Column(String(100))
    is_active     = Column(Boolean, nullable=False, default=True)
    created_at    = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at    = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action     = Column(String(100), nullable=False)
    path       = Column(String(500))
    method     = Column(String(10))
    ip         = Column(String(50))
    detail     = Column(JSON)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)


# ---------------------------------------------------------------------------
# Phase 01 — Data Capture & Training
# ---------------------------------------------------------------------------

class Soldier(Base):
    __tablename__ = "soldiers"

    id               = Column(Integer, primary_key=True, index=True)
    service_number   = Column(String(50), unique=True, nullable=False, index=True)
    rank             = Column(String(30), nullable=False)
    name             = Column(String(255), nullable=False)
    unit             = Column(String(100))
    mos              = Column(String(20))           # Military Occupational Specialty
    leader_type      = Column(String(50))           # squad_leader, team_leader, rifleman…
    is_active        = Column(Boolean, default=True)

    # Computed skill vector (0.0 – 1.0 per dimension)
    skill_leadership       = Column(Float, default=0.5)
    skill_decision_making  = Column(Float, default=0.5)
    skill_stress_tolerance = Column(Float, default=0.5)
    skill_tactical         = Column(Float, default=0.5)
    skill_communication    = Column(Float, default=0.5)
    skill_teamwork         = Column(Float, default=0.5)
    skill_adaptability     = Column(Float, default=0.5)
    skill_physical         = Column(Float, default=0.5)
    skill_technical        = Column(Float, default=0.5)

    decision_style   = Column(String(50), default="methodical")  # aggressive/methodical/adaptive
    leadership_traits = Column(JSON, default=list)               # ["decisive", "assertive"…]
    personality_profile = Column(JSON, default=dict)

    owner_user_id      = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at         = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at         = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    assessments  = relationship("Assessment",       back_populates="soldier", cascade="all, delete-orphan")
    team_members = relationship("TeamMember",        back_populates="soldier")
    readiness    = relationship("SoldierReadiness",  back_populates="soldier", uselist=False, cascade="all, delete-orphan")
    position     = relationship("SoldierPosition",   back_populates="soldier", uselist=False, cascade="all, delete-orphan")


class TrainingEvent(Base):
    __tablename__ = "training_events"

    id           = Column(Integer, primary_key=True, index=True)
    event_name   = Column(String(255), nullable=False)
    event_type   = Column(String(50), default="FTX")  # FTX, STX, live_fire, classroom, AAR
    event_date   = Column(String(20))                  # ISO date string
    location     = Column(String(255))
    mission_type = Column(String(50))                  # defend, attack, ambush…
    notes        = Column(Text)

    owner_user_id      = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at         = Column(DateTime(timezone=True), nullable=False, default=_now)

    assessments = relationship("Assessment", back_populates="event")


class Assessment(Base):
    __tablename__ = "assessments"

    id                = Column(Integer, primary_key=True, index=True)
    soldier_id        = Column(Integer, ForeignKey("soldiers.id", ondelete="CASCADE"), nullable=False)
    event_id          = Column(Integer, ForeignKey("training_events.id", ondelete="SET NULL"), nullable=True)
    evaluator_id      = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    assessment_type   = Column(String(50), default="field_eval")  # field_eval, classroom, aar, self
    capture_method    = Column(String(30), default="manual")      # manual, ocr, speech_to_text

    # Raw captured content (OCR/STT output or manual notes)
    raw_capture       = Column(Text)
    photo_url         = Column(String(500))
    audio_url         = Column(String(500))

    # AI analysis results
    ai_analyzed       = Column(Boolean, default=False)
    ai_summary        = Column(Text)                  # Human-readable AI summary
    ai_detail         = Column(JSON, default=dict)    # Full AI analysis JSON

    # Scored dimensions (0.0 – 5.0 scale)
    score_leadership      = Column(Float)
    score_decision_quality = Column(Float)
    score_stress_response  = Column(Float)
    score_tactical        = Column(Float)
    score_communication   = Column(Float)

    notes             = Column(Text)

    # Structured evaluation type (set when using the tabbed eval form)
    eval_category      = Column(String(20))       # leader_eval / unit_eval / steo_eval
    steo_mission_name  = Column(String(255))

    # Leader Evaluation category scores (1–5, T/P/U averaged)
    ldr_planning     = Column(Float)
    ldr_atd          = Column(Float)              # attention to detail
    ldr_time_mgmt    = Column(Float)
    ldr_decisiveness = Column(Float)
    ldr_tactics      = Column(Float)

    # Unit Mission Proficiency (UMP) category scores (1–5)
    ump_planning     = Column(Float)
    ump_atd          = Column(Float)
    ump_time_mgmt    = Column(Float)
    ump_decisiveness = Column(Float)
    ump_tactics      = Column(Float)

    owner_user_id      = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at         = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at         = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    soldier          = relationship("Soldier", back_populates="assessments")
    event            = relationship("TrainingEvent", back_populates="assessments")
    evaluator        = relationship("User", foreign_keys=[evaluator_id])
    detailed_ratings = relationship("DetailedRating", back_populates="assessment", cascade="all, delete-orphan")


class DetailedRating(Base):
    __tablename__ = "detailed_ratings"

    id                = Column(Integer, primary_key=True, index=True)
    assessment_id     = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    eval_type         = Column(String(20))    # leader / unit / steo
    task_group        = Column(String(100))   # Planning, Time Management, etc.
    task_name         = Column(String(255))   # for STEO: mission name
    subtask_number    = Column(Integer)
    subtask_description = Column(Text)
    rating            = Column(String(1))     # T / P / U
    rating_score      = Column(Integer)       # 1 / 3 / 5
    created_at        = Column(DateTime(timezone=True), nullable=False, default=_now)

    assessment = relationship("Assessment", back_populates="detailed_ratings")


# ---------------------------------------------------------------------------
# ATAK / Operational Context
# ---------------------------------------------------------------------------

class SoldierReadiness(Base):
    __tablename__ = "soldier_readiness"

    id               = Column(Integer, primary_key=True, index=True)
    soldier_id       = Column(Integer, ForeignKey("soldiers.id", ondelete="CASCADE"), nullable=False, unique=True)
    sleep_hours_24h  = Column(Float, default=8.0)   # hours slept in last 24h
    sleep_hours_48h  = Column(Float, default=16.0)  # hours slept in last 48h
    fatigue_index    = Column(Float, default=0.0)   # 0.0 = rested, 1.0 = severely fatigued (computed server-side)
    injury_status    = Column(String(30), default="fit")  # fit / light_duty / unfit
    updated_at       = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    soldier = relationship("Soldier", back_populates="readiness")


class SoldierPosition(Base):
    __tablename__ = "soldier_positions"

    id                  = Column(Integer, primary_key=True, index=True)
    soldier_id          = Column(Integer, ForeignKey("soldiers.id", ondelete="CASCADE"), nullable=False, unique=True)
    mgrs_grid           = Column(String(20))
    lat                 = Column(Float)
    lon                 = Column(Float)
    operational_status  = Column(String(30), default="available")  # available / on_mission / casualty / rest
    updated_at          = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    soldier = relationship("Soldier", back_populates="position")


class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"

    id             = Column(Integer, primary_key=True, index=True)
    mgrs_grid      = Column(String(20), nullable=False, index=True)
    temperature_c  = Column(Float)
    humidity_pct   = Column(Float)
    wind_speed_kmh = Column(Float)
    visibility_km  = Column(Float, default=10.0)
    wbgt           = Column(Float)   # Wet Bulb Globe Temperature — military heat stress standard
    precipitation  = Column(String(20), default="none")  # none / light / heavy
    recorded_at    = Column(DateTime(timezone=True), nullable=False, default=_now)
    created_at     = Column(DateTime(timezone=True), nullable=False, default=_now)


# ---------------------------------------------------------------------------
# Phase 02 — Team Optimization
# ---------------------------------------------------------------------------

class Mission(Base):
    __tablename__ = "missions"

    id                   = Column(Integer, primary_key=True, index=True)
    mission_name         = Column(String(255), nullable=False)
    mission_type         = Column(String(50), default="attack")  # defend/attack/ambush/raid/mtc/recon
    threat_level         = Column(String(20), default="medium")  # low/medium/high/extreme
    terrain_type         = Column(String(50), default="general") # urban/mountain/jungle/desert/arctic
    required_team_size   = Column(Integer, default=9)
    special_requirements = Column(JSON, default=list)            # ["airborne_qualified"…]
    duration_hours       = Column(Float, default=24.0)
    description          = Column(Text)
    status               = Column(String(30), default="planning") # planning/active/complete/cancelled
    selected_composition_id = Column(Integer, nullable=True)

    ao_grid_center      = Column(String(20))   # MGRS grid center of Area of Operations
    ao_radius_km        = Column(Float)
    weather_snapshot_id = Column(Integer, ForeignKey("weather_snapshots.id", ondelete="SET NULL"), nullable=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at         = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at         = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    compositions = relationship("TeamComposition", back_populates="mission", cascade="all, delete-orphan")


class TeamComposition(Base):
    __tablename__ = "team_compositions"

    id               = Column(Integer, primary_key=True, index=True)
    mission_id       = Column(Integer, ForeignKey("missions.id", ondelete="CASCADE"), nullable=False)
    composition_rank = Column(Integer, default=1)  # 1 = best option
    team_size        = Column(Integer)
    fit_score        = Column(Float, default=0.0)   # 0.0 – 1.0
    rationale        = Column(Text)                 # Explainable AI rationale
    is_selected      = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    mission = relationship("Mission", back_populates="compositions")
    members = relationship("TeamMember", back_populates="composition", cascade="all, delete-orphan")


class TeamMember(Base):
    __tablename__ = "team_members"

    id             = Column(Integer, primary_key=True, index=True)
    composition_id = Column(Integer, ForeignKey("team_compositions.id", ondelete="CASCADE"), nullable=False)
    soldier_id     = Column(Integer, ForeignKey("soldiers.id", ondelete="CASCADE"), nullable=False)
    role           = Column(String(50))    # team_lead, point, support, medic, comms…
    fit_score      = Column(Float, default=0.0)
    fit_notes      = Column(Text)

    composition = relationship("TeamComposition", back_populates="members")
    soldier     = relationship("Soldier", back_populates="team_members")


# ---------------------------------------------------------------------------
# Phase 03 — Adversarial AI Co-Pilot
# ---------------------------------------------------------------------------

class BattlespaceSession(Base):
    __tablename__ = "battlespace_sessions"

    id                   = Column(Integer, primary_key=True, index=True)
    session_name         = Column(String(255), nullable=False)
    status               = Column(String(20), default="active")  # active / closed
    mission_id           = Column(Integer, ForeignKey("missions.id", ondelete="SET NULL"), nullable=True)
    scenario_description = Column(Text)
    friendly_units       = Column(JSON, default=list)      # list of unit position dicts
    known_enemy          = Column(JSON, default=list)      # known enemy positions
    intel_reports        = Column(JSON, default=list)      # intel report strings

    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at         = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at         = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    sensor_tracks    = relationship("SensorTrack",    back_populates="session", cascade="all, delete-orphan")
    risk_vectors     = relationship("RiskVector",     back_populates="session", cascade="all, delete-orphan")
    simulations      = relationship("AdversarialSim", back_populates="session", cascade="all, delete-orphan")
    sim_jobs         = relationship("SimulationJob",  back_populates="session", cascade="all, delete-orphan")


class SensorTrack(Base):
    __tablename__ = "sensor_tracks"

    id          = Column(Integer, primary_key=True, index=True)
    session_id  = Column(Integer, ForeignKey("battlespace_sessions.id", ondelete="CASCADE"), nullable=False)
    track_type  = Column(String(20), default="friendly")  # friendly / enemy / unknown
    callsign    = Column(String(50))
    grid        = Column(String(20))       # e.g. "GP123456"
    heading_deg = Column(Integer)
    speed_kmh   = Column(Float)
    status      = Column(String(50))       # stationary, moving, engaged…
    reported_at = Column(DateTime(timezone=True), default=_now)
    created_at  = Column(DateTime(timezone=True), nullable=False, default=_now)

    session = relationship("BattlespaceSession", back_populates="sensor_tracks")


class RiskVector(Base):
    __tablename__ = "risk_vectors"

    id                = Column(Integer, primary_key=True, index=True)
    session_id        = Column(Integer, ForeignKey("battlespace_sessions.id", ondelete="CASCADE"), nullable=False)
    risk_type         = Column(String(50))   # ambush / flanking / air_threat / supply_line…
    severity          = Column(String(20), default="medium")  # low/medium/high/critical
    description       = Column(Text)
    affected_units    = Column(JSON, default=list)
    recommended_action = Column(Text)
    confidence_score  = Column(Float, default=0.0)
    ai_generated      = Column(Boolean, default=True)
    created_at        = Column(DateTime(timezone=True), nullable=False, default=_now)

    session = relationship("BattlespaceSession", back_populates="risk_vectors")


class AdversarialSim(Base):
    __tablename__ = "adversarial_sims"

    id                     = Column(Integer, primary_key=True, index=True)
    session_id             = Column(Integer, ForeignKey("battlespace_sessions.id", ondelete="CASCADE"), nullable=False)
    simulation_round       = Column(Integer, default=1)
    ai_model_used          = Column(String(100))
    adversary_moves        = Column(JSON, default=list)    # list of move descriptions
    risk_vectors_generated = Column(JSON, default=list)    # list of risk vector dicts
    recommendations        = Column(JSON, default=list)    # list of recommended actions
    raw_ai_response        = Column(Text)
    created_at             = Column(DateTime(timezone=True), nullable=False, default=_now)

    session = relationship("BattlespaceSession", back_populates="simulations")


class SimulationJob(Base):
    """Background simulation job — tracks status from pending → running → completed/failed."""
    __tablename__ = "simulation_jobs"

    id            = Column(Integer, primary_key=True, index=True)
    session_id    = Column(Integer, ForeignKey("battlespace_sessions.id", ondelete="CASCADE"), nullable=False)
    sim_round     = Column(Integer, default=1)
    status        = Column(String(20), default="pending")  # pending | running | completed | failed
    result        = Column(JSON)
    error         = Column(Text)
    ai_model_used = Column(String(100))
    created_at    = Column(DateTime(timezone=True), nullable=False, default=_now)
    completed_at  = Column(DateTime(timezone=True))

    session = relationship("BattlespaceSession", back_populates="sim_jobs")


# ---------------------------------------------------------------------------
# Phase 02 — Training Schedule (Platoon rotation)
# ---------------------------------------------------------------------------

class TrainingSchedule(Base):
    __tablename__ = "training_schedules"

    id                 = Column(Integer, primary_key=True, index=True)
    name               = Column(String(255), nullable=False)
    platoon_name       = Column(String(100))
    num_days           = Column(Integer, default=10)
    start_date         = Column(String(20))   # ISO date string e.g. "2026-05-05"
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at         = Column(DateTime(timezone=True), nullable=False, default=_now)

    slots = relationship("TrainingSlot", back_populates="schedule",
                         cascade="all, delete-orphan", order_by="TrainingSlot.id")


class TrainingSlot(Base):
    """One leadership assignment: day × mission × role → soldier."""
    __tablename__ = "training_slots"

    id          = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("training_schedules.id", ondelete="CASCADE"), nullable=False)
    day_number  = Column(Integer, nullable=False)           # 1 – num_days
    mission_type = Column(String(20), nullable=False)       # planning / attack / defense
    role        = Column(String(10), nullable=False)        # PL / PSG / SL1 / SL2 / SL3 / WSL
    soldier_id  = Column(Integer, ForeignKey("soldiers.id", ondelete="SET NULL"), nullable=True)

    schedule = relationship("TrainingSchedule", back_populates="slots")
    soldier  = relationship("Soldier")
