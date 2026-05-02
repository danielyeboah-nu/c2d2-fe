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
  // Structured eval fields
  eval_category?: string;
  steo_mission_name?: string;
  ldr_planning?: number;
  ldr_atd?: number;
  ldr_time_mgmt?: number;
  ldr_decisiveness?: number;
  ldr_tactics?: number;
  ump_planning?: number;
  ump_atd?: number;
  ump_time_mgmt?: number;
  ump_decisiveness?: number;
  ump_tactics?: number;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface LeaderAnalysis {
  soldier: { id: number; rank: string; name: string; unit?: string; mos?: string };
  eval_count: number;
  leader_averages: Record<string, number>;
  ump_averages: Record<string, number>;
  ai_averages: Record<string, number>;
  leader_trend: Record<string, string | number>[];
  ump_trend: Record<string, string | number>[];
  steo_summary: { mission: string; avg_score: number; proficiency: string; eval_count: number }[];
  assessments: Record<string, unknown>[];
}

export interface UnitAnalysis {
  unit: string;
  soldier_count: number;
  eval_count: number;
  per_soldier: {
    id: number; rank: string; name: string; eval_count: number;
    leader_averages: Record<string, number>;
    ump_averages: Record<string, number>;
  }[];
  unit_trend: Record<string, string | number>[];
  steo_summary: { mission: string; avg_score: number; proficiency: string; eval_count: number }[];
}

export interface BattalionOverview {
  total_soldiers: number;
  total_evals: number;
  battalion_leader_avg: Record<string, number>;
  battalion_ump_avg: Record<string, number>;
  units: {
    unit: string;
    soldier_count: number;
    eval_count: number;
    leader_averages: Record<string, number>;
    ump_averages: Record<string, number>;
  }[];
}

export interface SoldierReadiness {
  soldier_id: number;
  sleep_hours_24h: number;
  sleep_hours_48h: number;
  fatigue_index: number;          // 0.0 = rested, 1.0 = severely fatigued
  injury_status: "fit" | "light_duty" | "unfit";
  updated_at?: string;
}

export interface SoldierPosition {
  soldier_id: number;
  mgrs_grid?: string;
  lat?: number;
  lon?: number;
  operational_status: "available" | "on_mission" | "casualty" | "rest";
  updated_at?: string;
}

export interface WeatherSnapshot {
  id: number;
  mgrs_grid: string;
  temperature_c?: number;
  humidity_pct?: number;
  wind_speed_kmh?: number;
  visibility_km?: number;
  wbgt?: number;                  // Wet Bulb Globe Temperature
  precipitation: "none" | "light" | "heavy";
  recorded_at?: string;
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
  ao_grid_center?: string;        // MGRS grid center of Area of Operations
  ao_radius_km?: number;
  weather_snapshot_id?: number;
  compositions?: TeamComposition[];
}

export interface TeamMember {
  id: number;
  soldier_id: number;
  role: string;
  fit_score: number;              // contextual score (readiness + weather applied)
  base_fit_score?: number;        // raw skill-vector score before modifiers
  fit_notes?: string;             // human-readable modifier notes (e.g. "4.2h sleep ×0.75")
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
