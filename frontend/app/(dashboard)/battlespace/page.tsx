"use client";
import { useEffect, useState } from "react";
import { AlertTriangle, MapPin, Moon, Plus, Radio, Shield, Users, Zap } from "lucide-react";
import { api } from "@/lib/api";
import type { BattlespaceSession, SensorTrack, SoldierReadiness, SoldierPosition } from "@/types";

interface ForceSoldier {
  id: number;
  rank: string;
  name: string;
  unit?: string;
  readiness: SoldierReadiness | null;
  position: SoldierPosition | null;
}

interface ForceStatusResponse {
  soldiers: ForceSoldier[];
  kpis: { total: number; available: number; on_mission: number; casualty: number; rest: number; no_data: number };
}

type UnitPos = { callsign: string; grid?: string; status?: string };

interface AdversaryMove { move_type: string; description: string; target?: string; timing?: string; probability: string; }
interface SimRiskVector { risk_type: string; severity: string; description: string; affected_units: string[]; recommended_action: string; confidence_score: number; }
interface SimRecommendation { priority: string; action: string; rationale: string; }
interface SimResult { situation_summary?: string; adversary_moves: AdversaryMove[]; risk_vectors: SimRiskVector[]; recommendations: SimRecommendation[]; ai_model_used?: string; }

const SEVERITY_STYLE: Record<string, { bar: string; badge: string }> = {
  critical: { bar: "bg-red-500",     badge: "bg-red-500/20 text-red-400" },
  high:     { bar: "bg-[#f85149]",   badge: "bg-[#f85149]/20 text-[#f85149]" },
  medium:   { bar: "bg-[#f59e0b]",   badge: "bg-[#f59e0b]/20 text-[#f59e0b]" },
  low:      { bar: "bg-[#3fb950]",   badge: "bg-[#3fb950]/20 text-[#3fb950]" },
};

const OP_STYLE: Record<string, string> = {
  available:  "bg-[#3fb950]/10 text-[#3fb950] border border-[#3fb950]/30",
  on_mission: "bg-[#58a6ff]/10 text-[#58a6ff] border border-[#58a6ff]/30",
  rest:       "bg-[#8b949e]/10 text-[#8b949e] border border-[#30363d]",
  casualty:   "bg-[#f85149]/10 text-[#f85149] border border-[#f85149]/30",
};

const FATIGUE_COLOR = (fi: number) =>
  fi <= 0.20 ? "text-[#3fb950]" : fi <= 0.50 ? "text-[#f59e0b]" : "text-[#f85149]";

export default function BattlespacePage() {
  const [sessions, setSessions]         = useState<BattlespaceSession[]>([]);
  const [active, setActive]             = useState<BattlespaceSession | null>(null);
  const [simResult, setSimResult]       = useState<SimResult | null>(null);
  const [forceStatus, setForceStatus]   = useState<ForceStatusResponse | null>(null);
  const [loading, setLoading]           = useState(true);
  const [simLoading, setSimLoading]     = useState(false);
  const [showNew, setShowNew]           = useState(false);
  const [trackForm, setTrackForm]       = useState({ track_type: "friendly", callsign: "", grid: "" });
  const [error, setError]               = useState("");
  const [form, setForm] = useState({
    session_name: "", scenario_description: "",
    intel_report: "",
    friendly_callsign: "", friendly_grid: "",
    enemy_callsign: "", enemy_grid: "",
  });

  useEffect(() => {
    Promise.all([
      api.get<BattlespaceSession[]>("/api/v1/battlespace"),
      api.get<ForceStatusResponse>("/api/v1/soldiers/force-status").catch(() => null),
    ]).then(([s, fs]) => {
      setSessions(s);
      setForceStatus(fs);
    }).finally(() => setLoading(false));
  }, []);

  async function openSession(session: BattlespaceSession) {
    const full = await api.get<BattlespaceSession>(`/api/v1/battlespace/${session.id}`);
    setActive(full);
    setSimResult(null);
  }

  async function handleCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    try {
      const friendly = form.friendly_callsign
        ? [{ callsign: form.friendly_callsign, grid: form.friendly_grid }] : [];
      const enemy = form.enemy_callsign
        ? [{ callsign: form.enemy_callsign, grid: form.enemy_grid }] : [];
      const intel = form.intel_report ? [form.intel_report] : [];

      const s = await api.post<BattlespaceSession>("/api/v1/battlespace", {
        session_name: form.session_name,
        scenario_description: form.scenario_description,
        friendly_units: friendly,
        known_enemy: enemy,
        intel_reports: intel,
      });
      setSessions(prev => [s, ...prev]);
      setShowNew(false);
      await openSession(s);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  async function handleAddTrack(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!active) return;
    setError("");
    try {
      await api.post<SensorTrack>(`/api/v1/battlespace/${active.id}/sensor-tracks`, trackForm);
      const updated = await api.get<BattlespaceSession>(`/api/v1/battlespace/${active.id}`);
      setActive(updated);
      setTrackForm({ track_type: "friendly", callsign: "", grid: "" });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  async function handleSimulate() {
    if (!active) return;
    setSimLoading(true);
    setSimResult(null);
    setError("");
    try {
      const res = await api.post<SimResult>(
        `/api/v1/battlespace/${active.id}/simulate-adversary`, {}
      );
      setSimResult(res);
      const updated = await api.get<BattlespaceSession>(`/api/v1/battlespace/${active.id}`);
      setActive(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setSimLoading(false);
    }
  }

  const trackColor = (t: string) =>
    t === "friendly" ? "text-[#3fb950]" : t === "enemy" ? "text-[#f85149]" : "text-[#f59e0b]";

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-black text-white">Battlespace</h1>
          <p className="text-[#8b949e] text-xs mt-0.5">Phase 03 — Adversarial AI Co-Pilot</p>
        </div>
        <button onClick={() => setShowNew(!showNew)}
          className="flex items-center gap-1.5 px-3 py-2 bg-[#f85149] hover:bg-red-600 text-white text-sm font-semibold rounded-md transition-colors">
          <Plus size={14} /> New Session
        </button>
      </div>

      {error && <div className="p-3 bg-[#f85149]/10 border border-[#f85149]/30 text-[#f85149] text-sm rounded-md">{error}</div>}

      {/* New Session Form */}
      {showNew && (
        <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Create Battlespace Session</h2>
          <form onSubmit={handleCreate} className="space-y-3">
            <div>
              <label className="block text-[10px] text-[#8b949e] uppercase tracking-wider mb-1">Session Name *</label>
              <input required value={form.session_name}
                onChange={e => setForm(p => ({ ...p, session_name: e.target.value }))}
                className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none focus:border-[#f85149]" />
            </div>
            <div>
              <label className="block text-[10px] text-[#8b949e] uppercase tracking-wider mb-1">Scenario Description</label>
              <textarea value={form.scenario_description} rows={2}
                onChange={e => setForm(p => ({ ...p, scenario_description: e.target.value }))}
                placeholder="Describe the operational scenario, objective, and known conditions…"
                className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none resize-none" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] text-[#3fb950] uppercase tracking-wider mb-1">Friendly Callsign</label>
                <input value={form.friendly_callsign}
                  onChange={e => setForm(p => ({ ...p, friendly_callsign: e.target.value }))}
                  placeholder="e.g. Alpha-6"
                  className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none" />
              </div>
              <div>
                <label className="block text-[10px] text-[#3fb950] uppercase tracking-wider mb-1">Friendly Grid</label>
                <input value={form.friendly_grid}
                  onChange={e => setForm(p => ({ ...p, friendly_grid: e.target.value }))}
                  placeholder="e.g. GP123456"
                  className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none" />
              </div>
              <div>
                <label className="block text-[10px] text-[#f85149] uppercase tracking-wider mb-1">Enemy Callsign</label>
                <input value={form.enemy_callsign}
                  onChange={e => setForm(p => ({ ...p, enemy_callsign: e.target.value }))}
                  placeholder="e.g. OPFOR-1"
                  className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none" />
              </div>
              <div>
                <label className="block text-[10px] text-[#f85149] uppercase tracking-wider mb-1">Enemy Grid</label>
                <input value={form.enemy_grid}
                  onChange={e => setForm(p => ({ ...p, enemy_grid: e.target.value }))}
                  placeholder="e.g. GP789012"
                  className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none" />
              </div>
            </div>
            <div>
              <label className="block text-[10px] text-[#8b949e] uppercase tracking-wider mb-1">Intel Report</label>
              <input value={form.intel_report}
                onChange={e => setForm(p => ({ ...p, intel_report: e.target.value }))}
                placeholder="e.g. Enemy convoy observed moving north at 0600"
                className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none" />
            </div>
            <div className="flex gap-2">
              <button type="submit"
                className="px-4 py-2 bg-[#f85149] text-white text-sm font-semibold rounded-md hover:bg-red-600">Create</button>
              <button type="button" onClick={() => setShowNew(false)}
                className="px-4 py-2 bg-[#21262d] text-[#8b949e] text-sm rounded-md hover:text-white">Cancel</button>
            </div>
          </form>
        </div>
      )}

      {/* ── Force Status Panel ── */}
      {forceStatus && (
        <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
          <div className="flex items-center gap-2 mb-4">
            <Users size={15} className="text-[#f59e0b]" />
            <h2 className="text-sm font-semibold text-white">Force Status</h2>
            <span className="ml-auto text-[10px] text-[#6e7681]">{forceStatus.kpis.total} soldiers</span>
          </div>

          {/* KPI row */}
          <div className="grid grid-cols-4 gap-2 mb-4">
            {[
              { label: "Available",  count: forceStatus.kpis.available,  color: "text-[#3fb950]" },
              { label: "On Mission", count: forceStatus.kpis.on_mission,  color: "text-[#58a6ff]" },
              { label: "Rest",       count: forceStatus.kpis.rest,        color: "text-[#8b949e]" },
              { label: "Casualty",   count: forceStatus.kpis.casualty,    color: "text-[#f85149]" },
            ].map(k => (
              <div key={k.label} className="bg-[#0d1117] rounded p-2.5 text-center">
                <p className={`text-xl font-black ${k.color}`}>{k.count}</p>
                <p className="text-[10px] text-[#8b949e]">{k.label}</p>
              </div>
            ))}
          </div>

          {/* Soldier roster */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2">
            {forceStatus.soldiers.map(s => {
              const opStatus = s.position?.operational_status ?? "no_data";
              const styleClass = OP_STYLE[opStatus] ?? "bg-[#21262d] text-[#8b949e] border border-[#30363d]";
              const fatigue    = s.readiness?.fatigue_index;

              return (
                <div key={s.id} className="bg-[#0d1117] rounded-md px-3 py-2.5 flex items-start gap-2.5">
                  {/* Status dot */}
                  <div className={`mt-0.5 w-2 h-2 rounded-full shrink-0 ${
                    opStatus === "available"  ? "bg-[#3fb950]" :
                    opStatus === "on_mission" ? "bg-[#58a6ff]" :
                    opStatus === "casualty"   ? "bg-[#f85149]" :
                    opStatus === "rest"       ? "bg-[#8b949e]" : "bg-[#30363d]"
                  }`} />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-xs text-white truncate">
                        {s.rank} {s.name}
                      </span>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded capitalize shrink-0 ${styleClass}`}>
                        {opStatus === "no_data" ? "unknown" : opStatus.replace("_", " ")}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                      {s.unit && (
                        <span className="text-[10px] text-[#6e7681]">{s.unit}</span>
                      )}
                      {s.position?.mgrs_grid && (
                        <span className="flex items-center gap-0.5 text-[10px] text-[#f59e0b] font-mono">
                          <MapPin size={9} />{s.position.mgrs_grid}
                        </span>
                      )}
                      {fatigue != null && (
                        <span className={`flex items-center gap-0.5 text-[10px] ${FATIGUE_COLOR(fatigue)}`}>
                          <Moon size={9} />{Math.round(fatigue * 100)}% fatigue
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
            {forceStatus.kpis.no_data > 0 && (
              <div className="bg-[#0d1117] rounded-md px-3 py-2.5 flex items-center gap-2 col-span-full">
                <div className="w-2 h-2 rounded-full bg-[#30363d] shrink-0" />
                <span className="text-[10px] text-[#6e7681]">
                  {forceStatus.kpis.no_data} soldier{forceStatus.kpis.no_data !== 1 ? "s" : ""} with no position data
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Sessions + Active Session ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Sessions list */}
        <div className="space-y-2">
          <h2 className="text-xs font-semibold text-[#8b949e] uppercase tracking-wider">Sessions</h2>
          {loading ? (
            <div className="text-[#8b949e] text-sm">Loading…</div>
          ) : sessions.length === 0 ? (
            <div className="text-[#8b949e] text-sm">No sessions yet</div>
          ) : sessions.map(s => (
            <button key={s.id}
              onClick={() => openSession(s)}
              className={`w-full text-left px-4 py-3 rounded-lg border transition-colors ${
                active?.id === s.id
                  ? "border-[#f85149] bg-[#f85149]/10"
                  : "border-[#30363d] bg-[#161b22] hover:border-[#8b949e]"
              }`}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-white font-medium">{s.session_name}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                  s.status === "active" ? "bg-[#3fb950]/20 text-[#3fb950]" : "bg-[#30363d] text-[#8b949e]"
                }`}>{s.status}</span>
              </div>
              <p className="text-[10px] text-[#8b949e] truncate">{s.scenario_description ?? "No description"}</p>
            </button>
          ))}
        </div>

        {/* Active Session detail */}
        {active && (
          <div className="lg:col-span-2 space-y-4">
            {/* Session header */}
            <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h2 className="text-white font-semibold">{active.session_name}</h2>
                  <p className="text-xs text-[#8b949e] mt-0.5">{active.scenario_description}</p>
                </div>
                <button
                  onClick={handleSimulate}
                  disabled={simLoading || active.status === "closed"}
                  className="flex items-center gap-1.5 px-4 py-2 bg-[#f85149] hover:bg-red-600 text-white text-sm font-semibold rounded-md disabled:opacity-50 transition-colors"
                >
                  <Zap size={14} />
                  {simLoading ? "Simulating…" : "Run Simulation"}
                </button>
              </div>

              {/* Units grid */}
              <div className="grid grid-cols-2 gap-3 mt-4">
                <div className="bg-[#0d1117] rounded-md p-3">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Shield size={12} className="text-[#3fb950]" />
                    <span className="text-[10px] text-[#3fb950] uppercase tracking-wider font-semibold">Friendly</span>
                  </div>
                  {active.friendly_units.length === 0 ? (
                    <p className="text-[10px] text-[#6e7681]">None reported</p>
                  ) : active.friendly_units.map((u, i) => {
                    const unit = u as UnitPos;
                    return (
                      <p key={i} className="text-xs text-white">
                        {unit.callsign}
                        {unit.grid && <span className="ml-1 text-[#8b949e]">{unit.grid}</span>}
                      </p>
                    );
                  })}
                </div>
                <div className="bg-[#0d1117] rounded-md p-3">
                  <div className="flex items-center gap-1.5 mb-2">
                    <AlertTriangle size={12} className="text-[#f85149]" />
                    <span className="text-[10px] text-[#f85149] uppercase tracking-wider font-semibold">Enemy</span>
                  </div>
                  {active.known_enemy.length === 0 ? (
                    <p className="text-[10px] text-[#6e7681]">None reported</p>
                  ) : active.known_enemy.map((u, i) => {
                    const unit = u as UnitPos;
                    return (
                      <p key={i} className="text-xs text-white">
                        {unit.callsign}
                        {unit.grid && <span className="ml-1 text-[#8b949e]">{unit.grid}</span>}
                      </p>
                    );
                  })}
                </div>
              </div>

              {/* Intel */}
              {active.intel_reports.length > 0 && (
                <div className="mt-3">
                  <p className="text-[10px] text-[#8b949e] uppercase tracking-wider mb-1">Intel Reports</p>
                  {active.intel_reports.map((r, i) => (
                    <p key={i} className="text-xs text-[#8b949e] border-l-2 border-[#f59e0b] pl-2 mb-1">{r}</p>
                  ))}
                </div>
              )}
            </div>

            {/* Add Track */}
            <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <Radio size={14} className="text-[#8b949e]" />
                <h3 className="text-sm font-semibold text-white">Add Sensor Track</h3>
              </div>
              <form onSubmit={handleAddTrack} className="flex gap-2">
                <select value={trackForm.track_type}
                  onChange={e => setTrackForm(p => ({ ...p, track_type: e.target.value }))}
                  className="px-2.5 py-1.5 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none w-28">
                  {["friendly","enemy","unknown"].map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <input required value={trackForm.callsign}
                  onChange={e => setTrackForm(p => ({ ...p, callsign: e.target.value }))}
                  placeholder="Callsign"
                  className="flex-1 px-2.5 py-1.5 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none" />
                <input value={trackForm.grid}
                  onChange={e => setTrackForm(p => ({ ...p, grid: e.target.value }))}
                  placeholder="Grid"
                  className="w-28 px-2.5 py-1.5 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none" />
                <button type="submit"
                  className="px-3 py-1.5 bg-[#21262d] text-[#8b949e] hover:text-white text-sm rounded-md">Add</button>
              </form>
              {(active.sensor_tracks?.length ?? 0) > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {active.sensor_tracks?.map(t => (
                    <span key={t.id} className={`text-[10px] px-2 py-0.5 bg-[#0d1117] rounded border border-[#30363d] ${trackColor(t.track_type)}`}>
                      {t.callsign} {t.grid && `(${t.grid})`}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Simulation Result */}
            {simResult && (
              <div className="bg-[#161b22] border border-[#f85149]/40 rounded-lg p-5 space-y-4">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-[#f85149] animate-pulse" />
                  <h3 className="text-sm font-semibold text-white">ATHENA — Adversarial Analysis</h3>
                </div>

                {simResult.situation_summary && (
                  <p className="text-sm text-[#8b949e] leading-relaxed border-l-2 border-[#f85149] pl-3">
                    {simResult.situation_summary}
                  </p>
                )}

                {simResult.adversary_moves?.length > 0 && (
                  <div>
                    <h4 className="text-[10px] text-[#f85149] uppercase tracking-wider mb-2">Likely Adversary Moves</h4>
                    <div className="space-y-2">
                      {simResult.adversary_moves.map((m, i) => (
                        <div key={i} className="bg-[#0d1117] rounded-md p-3">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-[10px] px-1.5 py-0.5 bg-[#f85149]/20 text-[#f85149] rounded capitalize">
                              {m.move_type}
                            </span>
                            <span className={`text-[10px] ${
                              m.probability === "high"   ? "text-[#f85149]" :
                              m.probability === "medium" ? "text-[#f59e0b]" : "text-[#3fb950]"
                            }`}>{m.probability} prob.</span>
                          </div>
                          <p className="text-xs text-[#e6edf3]">{m.description}</p>
                          {m.timing && <p className="text-[10px] text-[#8b949e] mt-0.5">Timing: {m.timing}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {simResult.risk_vectors?.length > 0 && (
                  <div>
                    <h4 className="text-[10px] text-[#f59e0b] uppercase tracking-wider mb-2">Risk Vectors</h4>
                    <div className="space-y-2">
                      {simResult.risk_vectors.map((rv, i) => {
                        const style = SEVERITY_STYLE[rv.severity] ?? SEVERITY_STYLE.medium;
                        return (
                          <div key={i} className="bg-[#0d1117] rounded-md p-3">
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${style.badge}`}>
                                {rv.severity}
                              </span>
                              <span className="text-[10px] text-[#8b949e] capitalize">{rv.risk_type.replace(/_/g, " ")}</span>
                            </div>
                            <p className="text-xs text-[#e6edf3] mb-1">{rv.description}</p>
                            <p className="text-[10px] text-[#3fb950]">Action: {rv.recommended_action}</p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {simResult.recommendations?.length > 0 && (
                  <div>
                    <h4 className="text-[10px] text-[#3fb950] uppercase tracking-wider mb-2">Recommendations</h4>
                    <div className="space-y-2">
                      {simResult.recommendations.map((r, i) => (
                        <div key={i} className="flex gap-3 bg-[#0d1117] rounded-md p-3">
                          <span className={`text-[10px] px-1.5 py-0.5 h-fit rounded font-bold uppercase shrink-0 ${
                            r.priority === "immediate"  ? "bg-[#f85149]/20 text-[#f85149]" :
                            r.priority === "short_term" ? "bg-[#f59e0b]/20 text-[#f59e0b]" :
                            "bg-[#21262d] text-[#8b949e]"
                          }`}>{r.priority}</span>
                          <div>
                            <p className="text-xs text-white">{r.action}</p>
                            <p className="text-[10px] text-[#8b949e] mt-0.5">{r.rationale}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Persisted Risk Vectors */}
            {!simResult && (active.risk_vectors?.length ?? 0) > 0 && (
              <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
                <h3 className="text-sm font-semibold text-white mb-3">Identified Risk Vectors</h3>
                <div className="space-y-2">
                  {active.risk_vectors?.map(rv => {
                    const style = SEVERITY_STYLE[rv.severity] ?? SEVERITY_STYLE.medium;
                    return (
                      <div key={rv.id} className="bg-[#0d1117] rounded-md p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${style.badge}`}>
                            {rv.severity}
                          </span>
                          <span className="text-[10px] text-[#8b949e] capitalize">{rv.risk_type.replace(/_/g, " ")}</span>
                        </div>
                        <p className="text-xs text-[#e6edf3]">{rv.description}</p>
                        <p className="text-[10px] text-[#3fb950] mt-0.5">Action: {rv.recommended_action}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
