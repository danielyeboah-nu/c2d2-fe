"""
Seed C2D2 demo data — soldiers, training events, a mission, and a battlespace session.
Run from the repo root: python scripts/seed_demo_data.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv(".env")

from backend.app.db.database import init_db, get_session_factory
from backend.app.db.models import Soldier, TrainingEvent, Mission, BattlespaceSession, User
from backend.app.services.auth_service import hash_password

def seed():
    init_db()
    SessionLocal = get_session_factory()
    db = SessionLocal()

    # Admin user
    if not db.query(User).filter(User.email == "admin@c2d2.local").first():
        db.add(User(email="admin@c2d2.local", password_hash=hash_password("changeme123"),
                    full_name="C2D2 Admin", role="commander"))
        db.commit()

    admin = db.query(User).filter(User.email == "admin@c2d2.local").first()

    # Soldiers
    soldiers_data = [
        dict(service_number="US-001", rank="SSG", name="Torres, Marcus",   unit="Alpha Co", mos="11B",
             leader_type="squad_leader", decision_style="aggressive",
             skill_leadership=0.85, skill_decision_making=0.78, skill_stress_tolerance=0.82,
             skill_tactical=0.88, skill_communication=0.75, skill_teamwork=0.80, skill_adaptability=0.72,
             leadership_traits=["decisive", "assertive", "tactical"]),
        dict(service_number="US-002", rank="SGT", name="Kim, Ji-Young",    unit="Alpha Co", mos="11B",
             leader_type="team_leader", decision_style="methodical",
             skill_leadership=0.72, skill_decision_making=0.85, skill_stress_tolerance=0.68,
             skill_tactical=0.80, skill_communication=0.90, skill_teamwork=0.88, skill_adaptability=0.77,
             leadership_traits=["analytical", "communicative", "calm"]),
        dict(service_number="US-003", rank="SPC", name="Rivera, Elena",    unit="Alpha Co", mos="11B",
             leader_type="rifleman", decision_style="adaptive",
             skill_leadership=0.55, skill_decision_making=0.70, skill_stress_tolerance=0.75,
             skill_tactical=0.65, skill_communication=0.60, skill_teamwork=0.85, skill_adaptability=0.92,
             leadership_traits=["adaptive", "resilient"]),
        dict(service_number="US-004", rank="SGT", name="Okafor, Emeka",   unit="Bravo Co", mos="11B",
             leader_type="team_leader", decision_style="aggressive",
             skill_leadership=0.78, skill_decision_making=0.72, skill_stress_tolerance=0.88,
             skill_tactical=0.82, skill_communication=0.65, skill_teamwork=0.70, skill_adaptability=0.68,
             leadership_traits=["fearless", "decisive", "physical"]),
        dict(service_number="US-005", rank="SPC", name="Patel, Anika",    unit="Bravo Co", mos="25U",
             leader_type="comms", decision_style="methodical",
             skill_leadership=0.50, skill_decision_making=0.75, skill_stress_tolerance=0.62,
             skill_tactical=0.55, skill_communication=0.95, skill_teamwork=0.78, skill_adaptability=0.70,
             leadership_traits=["technical", "precise"]),
        dict(service_number="US-006", rank="SPC", name="Hernandez, Luis", unit="Bravo Co", mos="68W",
             leader_type="medic", decision_style="adaptive",
             skill_leadership=0.58, skill_decision_making=0.80, skill_stress_tolerance=0.90,
             skill_tactical=0.60, skill_communication=0.72, skill_teamwork=0.82, skill_adaptability=0.85,
             leadership_traits=["calm_under_fire", "empathetic"]),
        dict(service_number="US-007", rank="SSG", name="Chen, David",     unit="Charlie Co", mos="11A",
             leader_type="squad_leader", decision_style="methodical",
             skill_leadership=0.90, skill_decision_making=0.88, skill_stress_tolerance=0.76,
             skill_tactical=0.85, skill_communication=0.82, skill_teamwork=0.75, skill_adaptability=0.80,
             leadership_traits=["strategic", "composed", "experienced"]),
        dict(service_number="US-008", rank="SPC", name="Wallace, Jamal",  unit="Charlie Co", mos="11B",
             leader_type="rifleman", decision_style="aggressive",
             skill_leadership=0.48, skill_decision_making=0.62, skill_stress_tolerance=0.80,
             skill_tactical=0.70, skill_communication=0.55, skill_teamwork=0.65, skill_adaptability=0.58,
             leadership_traits=["bold", "physical"]),
        dict(service_number="US-009", rank="CPL", name="Nguyen, Tran",    unit="Alpha Co", mos="11B",
             leader_type="team_leader", decision_style="adaptive",
             skill_leadership=0.68, skill_decision_making=0.74, skill_stress_tolerance=0.72,
             skill_tactical=0.78, skill_communication=0.70, skill_teamwork=0.88, skill_adaptability=0.82,
             leadership_traits=["collaborative", "situationally_aware"]),
    ]

    for sd in soldiers_data:
        if not db.query(Soldier).filter(Soldier.service_number == sd["service_number"]).first():
            traits = sd.pop("leadership_traits", [])
            s = Soldier(**sd, leadership_traits=traits, owner_user_id=admin.id, created_by_user_id=admin.id)
            db.add(s)
    db.commit()

    # Training Events
    events_data = [
        dict(event_name="JRTC Rotation 25-03", event_type="FTX", event_date="2025-03-10",
             location="Fort Polk, LA", mission_type="attack"),
        dict(event_name="Alpha Co STX — Live Fire", event_type="STX", event_date="2025-04-22",
             location="Range 12", mission_type="defend"),
        dict(event_name="NTC Rotation 25-07", event_type="FTX", event_date="2025-07-14",
             location="Fort Irwin, CA", mission_type="mtc"),
    ]
    for ed in events_data:
        if not db.query(TrainingEvent).filter(TrainingEvent.event_name == ed["event_name"]).first():
            db.add(TrainingEvent(**ed, owner_user_id=admin.id, created_by_user_id=admin.id))
    db.commit()

    # Mission
    if not db.query(Mission).filter(Mission.mission_name == "DEMO — Raid on OBJ HAWK").first():
        db.add(Mission(
            mission_name="DEMO — Raid on OBJ HAWK",
            mission_type="raid",
            threat_level="high",
            terrain_type="urban",
            required_team_size=6,
            description="Platoon raid on suspected HVT compound. Urban environment, night conditions.",
            created_by_user_id=admin.id,
        ))
        db.commit()

    # Battlespace Session
    if not db.query(BattlespaceSession).filter(BattlespaceSession.session_name == "DEMO — Op SHADOW LANCE").first():
        db.add(BattlespaceSession(
            session_name="DEMO — Op SHADOW LANCE",
            scenario_description="Platoon patrol sector north of FOB ATLAS. Intel indicates OPFOR elements staging ambush positions along Route ORANGE.",
            friendly_units=[
                {"callsign": "Alpha-6", "grid": "GP123456", "status": "stationary"},
                {"callsign": "Alpha-1", "grid": "GP124460", "status": "moving"},
            ],
            known_enemy=[
                {"callsign": "OPFOR-1", "grid": "GP130470", "status": "stationary"},
            ],
            intel_reports=[
                "0530: Two OPFOR vehicles observed moving north on Route ORANGE.",
                "0615: Local national reports armed personnel near grid GP135475.",
            ],
            created_by_user_id=admin.id,
        ))
        db.commit()

    db.close()
    print("Demo data seeded successfully.")
    print("Login: admin@c2d2.local / changeme123")

if __name__ == "__main__":
    seed()
