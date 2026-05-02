"""
Evaluation rubric data — Leader Eval, Unit Eval, SQD ST&EO.
Mirrors the Mtn-Bn eval_reference.csv structure.
Rating scale: T (Trained) = 5, P (Partially Trained) = 3, U (Untrained) = 1
"""
from __future__ import annotations

RATING_SCORES = {"T": 5, "P": 3, "U": 1}


# ---------------------------------------------------------------------------
# Leader Evaluation — 5 categories, 25 subtasks
# ---------------------------------------------------------------------------

LEADER_EVAL: list[dict] = [
    {
        "task_group": "Planning",
        "subtasks": [
            {"number": 1, "description": "Conducts detailed terrain and mission analysis (METT-TC)"},
            {"number": 2, "description": "Uses proper tactical tasks and operational overlay symbols"},
            {"number": 3, "description": "Creates plan that fits commander's intent and end state"},
            {"number": 4, "description": "Creates indirect fire (IDF) plan with targets and triggers"},
            {"number": 5, "description": "Creates DFCMs IAW unit SOP and battle drills"},
            {"number": 6, "description": "Briefs plan off terrain model with all subordinates present"},
        ],
    },
    {
        "task_group": "Time Management",
        "subtasks": [
            {"number": 1, "description": "Applies 1/3 – 2/3 rule and adheres to planning timeline"},
            {"number": 2, "description": "Conducts route planning and establishes hit times for each phase"},
            {"number": 3, "description": "Meets specified SP, phase line, and objective hit times"},
        ],
    },
    {
        "task_group": "Attention to Detail",
        "subtasks": [
            {"number": 1, "description": "Gives confirmation backbrief to O/C/T covering all five-paragraph OPORD elements"},
            {"number": 2, "description": "Conducts thorough MWE PCIs for all assigned equipment"},
            {"number": 3, "description": "Includes all critical information from higher OPORD and commander's intent"},
            {"number": 4, "description": "Identifies and assigns special teams (breach, assault, support, casualty collection)"},
            {"number": 5, "description": "Plans and resources rehearsals appropriate to time and mission complexity"},
        ],
    },
    {
        "task_group": "Tactics",
        "subtasks": [
            {"number": 1, "description": "Selects appropriate movement formation and technique for terrain and threat"},
            {"number": 2, "description": "Monitors and maintains 360° security during all phases of movement"},
            {"number": 3, "description": "Maintains positive control of element via clear orders and battle tracking"},
            {"number": 4, "description": "Conducts leader's recon prior to issuing orders or conducting rehearsals"},
            {"number": 5, "description": "Establishes ORP, attack position, and assault position IAW doctrinal standards"},
            {"number": 6, "description": "Effectively employs crew-served weapons, fires, and DFCMs on objective"},
            {"number": 7, "description": "Executes plan with controlled aggression and sound small-unit tactics on OBJ"},
        ],
    },
    {
        "task_group": "Decisiveness",
        "subtasks": [
            {"number": 1, "description": "Hits planned SP time with element ready and inspected"},
            {"number": 2, "description": "Balances time constraints with thorough mission preparation requirements"},
            {"number": 3, "description": "Reacts quickly and effectively to unanticipated mission changes or FRAGO"},
            {"number": 4, "description": "Demonstrates decisive leadership during actions on objective"},
        ],
    },
]


# ---------------------------------------------------------------------------
# Unit Evaluation (UMP) — 5 categories, 24 subtasks
# ---------------------------------------------------------------------------

UNIT_EVAL: list[dict] = [
    {
        "task_group": "Planning",
        "subtasks": [
            {"number": 1, "description": "NCO support channel initiates movement preparation and resource tracking"},
            {"number": 2, "description": "Unit conducts logistics planning (ammunition, water, food, batteries, medical)"},
            {"number": 3, "description": "Unit constructs and briefs off terrain model with all key leaders present"},
            {"number": 4, "description": "All leaders conduct TLPs and issue orders to their subordinates"},
            {"number": 5, "description": "Point man and navigators designated and rehearsed prior to SP"},
            {"number": 6, "description": "Special teams (breach, assault, support, CASEVAC) identified and assigned"},
            {"number": 7, "description": "Medical planning completed — CCP location, 9-line MEDEVAC, blood types known"},
            {"number": 8, "description": "Subordinate elements complete own TLPs nested within higher timeline"},
        ],
    },
    {
        "task_group": "Time Management",
        "subtasks": [
            {"number": 1, "description": "Subordinate TLPs conducted within time allocated by leader's 1/3 – 2/3 rule"},
            {"number": 2, "description": "OPORD issued NLT 2/3 of remaining planning time per leader's timeline"},
            {"number": 3, "description": "Unit crosses SP at designated time with accountability complete"},
            {"number": 4, "description": "Mission phases executed within designated time windows and hit times"},
        ],
    },
    {
        "task_group": "Attention to Detail",
        "subtasks": [
            {"number": 1, "description": "All soldiers conduct PCCs and PCIs on individual and crew-served equipment"},
            {"number": 2, "description": "Equipment allocation and sustainment loads distributed IAW OPORD annexes"},
            {"number": 3, "description": "Each echelon gives confirmation backbrief to their higher headquarters"},
            {"number": 4, "description": "Rehearsals conducted — battle drill, actions on contact, OBJ actions, CASEVAC"},
            {"number": 5, "description": "DFCMs and IDF targets briefed to all soldiers who may need to trigger them"},
            {"number": 6, "description": "Communications plan tested and primary/alternate/contingency established"},
        ],
    },
    {
        "task_group": "Tactics",
        "subtasks": [
            {"number": 1, "description": "Unit maintains noise and light discipline throughout all phases of operation"},
            {"number": 2, "description": "Security teams and overwatch elements properly positioned at all halts"},
            {"number": 3, "description": "Soldier and weapon discipline maintained — no accidental discharges or fratricide risk"},
            {"number": 4, "description": "ORP occupied with proper security and patrol base procedures followed"},
        ],
    },
    {
        "task_group": "Decisiveness",
        "subtasks": [
            {"number": 1, "description": "Element executes actions on objective with speed and violence of action"},
            {"number": 2, "description": "Subordinate leaders demonstrate initiative and adapt to changing conditions"},
        ],
    },
]


# ---------------------------------------------------------------------------
# SQD ST&EO — 7 mission types
# ---------------------------------------------------------------------------

STEO_MISSIONS: list[dict] = [
    {
        "mission": "Conduct an Ambush - Squad (07-SQD-9010)",
        "subtasks": [
            {"number": 1, "description": "Selects and occupies ambush site with proper security and cover/concealment"},
            {"number": 2, "description": "Establishes kill zone with interlocking fields of fire"},
            {"number": 3, "description": "Emplaces early warning devices and initiating device"},
            {"number": 4, "description": "Initiates ambush at correct trigger point with all fires massed"},
            {"number": 5, "description": "Assaults through kill zone after suppression, conducting SSE"},
            {"number": 6, "description": "Consolidates on objective, establishes security, and accounts for all personnel"},
            {"number": 7, "description": "Conducts withdrawal IAW plan and returns to friendly lines"},
        ],
    },
    {
        "mission": "Conduct an Attack - Squad (07-SQD-1092)",
        "subtasks": [
            {"number": 1, "description": "Occupies attack position and confirms objective orientation"},
            {"number": 2, "description": "Issues FRAGO or confirmatory orders to all fire team leaders"},
            {"number": 3, "description": "Moves from attack position to assault position using covered/concealed route"},
            {"number": 4, "description": "Establishes support element with appropriate sectors of fire"},
            {"number": 5, "description": "Assault element moves to breach point using fire and movement"},
            {"number": 6, "description": "Breaches or clears entry point under suppression from support element"},
            {"number": 7, "description": "Clears objective using proper room/trench clearing techniques"},
            {"number": 8, "description": "Consolidates on objective and establishes all-round defense"},
            {"number": 9, "description": "Conducts CASEVAC plan if casualties occur during assault"},
            {"number": 10, "description": "Performs SSE on objective IAW higher intelligence requirements"},
            {"number": 11, "description": "Establishes EPW handling procedures"},
            {"number": 12, "description": "Conducts reorganization and moves to subsequent positions"},
        ],
    },
    {
        "mission": "Conduct Area Reconnaissance - Squad (19-SQD-27040)",
        "subtasks": [
            {"number": 1, "description": "Issues recon objective and specific information requirements (SIRs) to element"},
            {"number": 2, "description": "Selects covered/concealed route to ORP and objective rally point"},
            {"number": 3, "description": "Occupies ORP and establishes security with small recon element"},
            {"number": 4, "description": "Conducts leader's recon of objective area prior to full element movement"},
            {"number": 5, "description": "Recon element moves to objective using proper spacing and security"},
            {"number": 6, "description": "Collects all SIR data using SALUTE format and sketches"},
            {"number": 7, "description": "Maintains noise and light discipline throughout recon"},
            {"number": 8, "description": "Identifies and reports obstacles, enemy positions, and avenues of approach"},
            {"number": 9, "description": "Conducts time-distance analysis for routes and alternates"},
            {"number": 10, "description": "Returns to ORP and consolidates all collected information"},
            {"number": 11, "description": "Submits complete SALUTE/SPOTREP to higher headquarters"},
            {"number": 12, "description": "Returns to friendly lines using alternate route"},
        ],
    },
    {
        "mission": "Conduct a Movement to Contact (07-PLT-1071)",
        "subtasks": [
            {"number": 1, "description": "Issues order with clear commander's intent and orientation on enemy"},
            {"number": 2, "description": "Selects formation appropriate to terrain, visibility, and threat"},
            {"number": 3, "description": "Establishes point element with proper spacing to prevent mass casualties"},
            {"number": 4, "description": "Maintains 360° security during movement at all times"},
            {"number": 5, "description": "Conducts proper actions on contact (react, report, return fire, reduce)"},
            {"number": 6, "description": "Employs crew-served weapons to gain fire superiority"},
            {"number": 7, "description": "Maneuvers an element to flank and destroy enemy position"},
            {"number": 8, "description": "Establishes communications with higher and reports contact"},
            {"number": 9, "description": "Maintains accountability of personnel throughout movement and contact"},
            {"number": 10, "description": "Conducts CASEVAC for wounded soldiers under fire"},
            {"number": 11, "description": "Consolidates and reorganizes after actions on contact"},
            {"number": 12, "description": "Continues mission or establishes hasty defense as directed"},
        ],
    },
    {
        "mission": "React to Direct Fire Contact - Dismounted (07-SQD-D9501)",
        "subtasks": [
            {"number": 1, "description": "Immediately returns fire in direction of contact"},
            {"number": 2, "description": "Soldiers seek covered and concealed positions"},
            {"number": 3, "description": "Leader identifies enemy position and reports to higher"},
            {"number": 4, "description": "Leader initiates fire and movement to gain fire superiority"},
            {"number": 5, "description": "Element suppresses enemy with crew-served weapons if available"},
            {"number": 6, "description": "Bounding element moves using rush and crawl techniques"},
            {"number": 7, "description": "Element breaks contact or maneuvers to destroy enemy IAW leader's order"},
            {"number": 8, "description": "Casualty assessment conducted and CASEVAC initiated if required"},
            {"number": 9, "description": "Element consolidates and reports status to higher"},
            {"number": 10, "description": "Continues mission or establishes defensive position"},
        ],
    },
    {
        "mission": "React to Indirect Fire - Dismounted (07-SQD-D9504)",
        "subtasks": [
            {"number": 1, "description": "Soldiers immediately move out of impact area at first round"},
            {"number": 2, "description": "Leader gives direction and distance to move out of impact area"},
            {"number": 3, "description": "Element moves rapidly to covered positions away from impact area"},
            {"number": 4, "description": "Leader establishes security and accounts for all personnel"},
            {"number": 5, "description": "Leader reports grid of impact area, direction of fire, and number of rounds"},
            {"number": 6, "description": "CASEVAC initiated for any casualties with proper 9-line submitted"},
            {"number": 7, "description": "Element continues to move until outside indirect fire range"},
            {"number": 8, "description": "Counter-battery request submitted if fire support assets available"},
            {"number": 9, "description": "Element reorganizes and continues mission or returns to friendly lines"},
        ],
    },
    {
        "mission": "React to Small UAS (Counter-UAS)",
        "subtasks": [
            {"number": 1, "description": "Soldiers identify and report UAS contact using SALUTE format"},
            {"number": 2, "description": "Element immediately disperses to reduce signature and target density"},
            {"number": 3, "description": "Leader reports UAS sighting to higher with type, direction, altitude"},
            {"number": 4, "description": "Soldiers cease use of electronic devices that may increase signature"},
            {"number": 5, "description": "Element moves to covered/concealed positions and minimizes movement"},
            {"number": 6, "description": "Designated soldiers engage UAS with organic weapons if ROE permits"},
            {"number": 7, "description": "Element employs camouflage and concealment to defeat UAS observation"},
            {"number": 8, "description": "Alternate route selected to avoid UAS coverage area"},
            {"number": 9, "description": "Maintains dispersion and concealment until UAS threat cleared by higher"},
        ],
    },
]


def get_reference(eval_type: str) -> list[dict]:
    """Return reference data for the given eval type."""
    if eval_type == "leader":
        return LEADER_EVAL
    if eval_type == "unit":
        return UNIT_EVAL
    if eval_type == "steo":
        return STEO_MISSIONS
    return []


def score_from_rating(rating: str) -> int:
    return RATING_SCORES.get(rating.upper(), 3)


def aggregate_category_scores(ratings: list[dict], eval_type: str) -> dict[str, float]:
    """
    Given a list of rating dicts (task_group, subtask_number, rating),
    return a dict of {category: avg_score} for the given eval type.
    """
    buckets: dict[str, list[float]] = {}
    for r in ratings:
        tg = r.get("task_group", "")
        score = score_from_rating(r.get("rating", "P"))
        buckets.setdefault(tg, []).append(float(score))

    return {tg: round(sum(vals) / len(vals), 2) for tg, vals in buckets.items() if vals}
