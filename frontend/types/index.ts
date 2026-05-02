export interface User {
  id: number;
  email: string;
  full_name?: string;
  role: "commander" | "evaluator" | "analyst" | "viewer";
  unit?: string;
}

export interface SkillVector {
  leadership: number;
  decision_making: number;
  stress_tolerance: number;
  tactical: number;
  communication: number;
  teamwork: number;
  adaptability: number;
  physical: number;
  technical: number;
}

export interface Soldier {
  id: number;
  service_number: string;
  rank: string;
  name: string;
  unit?: string;
  mos?: string;
  leader_type?: string;
  is_active: boolean;
  decision_style: string;
  leadership_traits: string[];
  skill_vector: SkillVector;
  created_at?: string;
  updated_at?: string;
}

export interface TrainingEvent {
  id: number;
  event_name: string;
  event_type: string;
  event_date?: string;
  location?: string;
  mission_type?: string;
  notes?: string;
}

export interface Assessment {
  id: number;
  soldier_id: number;
  event_id?: number;
  assessment_type: string;
  capture_method: string;
  raw_capture?: string;
  photo_url?: string;
  audio_url?: string;
  ai_analyzed: boolean;
  ai_summary?: string;
  ai_detail?: Record<string, unknown>;
  score_leadership?: number;
  score_decision_quality?: number;
  score_stress_response?: number;
  score_tactical?: number;
  score_communication?: number;
  notes?: string;
  created_at?: string;
}

export interface Mission {
  id: number;
  mission_name: string;
  mission_type: string;
  threat_level: string;
  terrain_type: string;
  required_team_size: number;
  special_requirements: string[];
  duration_hours: number;
  description?: string;
  status: string;
  selected_composition_id?: number;
  compositions?: TeamComposition[];
}

export interface TeamMember {
  id: number;
  soldier_id: number;
  role: string;
  fit_score: number;
  fit_notes?: string;
  name: string;
  unit?: string;
}

export interface TeamComposition {
  id: number;
  mission_id: number;
  composition_rank: number;
  team_size: number;
  fit_score: number;
  rationale: string;
  is_selected: boolean;
  members: TeamMember[];
}

export interface SensorTrack {
  id: number;
  track_type: "friendly" | "enemy" | "unknown";
  callsign: string;
  grid?: string;
  heading_deg?: number;
  speed_kmh?: number;
  status?: string;
}

export interface RiskVector {
  id: number;
  risk_type: string;
  severity: "critical" | "high" | "medium" | "low";
  description: string;
  affected_units: string[];
  recommended_action: string;
  confidence_score: number;
  created_at?: string;
}

export interface BattlespaceSession {
  id: number;
  session_name: string;
  status: "active" | "closed";
  mission_id?: number;
  scenario_description?: string;
  friendly_units: Record<string, unknown>[];
  known_enemy: Record<string, unknown>[];
  intel_reports: string[];
  sensor_tracks?: SensorTrack[];
  risk_vectors?: RiskVector[];
  created_at?: string;
}
