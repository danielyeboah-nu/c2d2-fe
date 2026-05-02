"use client";
import { useEffect, useState } from "react";
import { CheckCircle, ChevronDown, ChevronUp, Plus, Zap } from "lucide-react";
import { api } from "@/lib/api";
import type { Mission, TeamComposition } from "@/types";

const MISSION_TYPES = ["attack","defend","ambush","raid","mtc","recon"];
const THREAT_LEVELS = ["low","medium","high","extreme"];
const TERRAIN_TYPES = ["general","urban","mountain","jungle","desert","arctic"];

function FitBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 75 ? "bg-[#3fb950]" : pct >= 55 ? "bg-[#f59e0b]" : "bg-[#f85149]";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-[#30363d] rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm font-bold text-white w-10 text-right">{pct}%</span>
    </div>
  );
}

export default function TeamsPage() {
  const [missions, setMissions]       = useState<Mission[]>([]);
  const [loading, setLoading]         = useState(true);
  const [showNew, setShowNew]         = useState(false);
  const [optimizing, setOptimizing]   = useState<number | null>(null);
  const [expanded, setExpanded]       = useState<number | null>(null);
  const [selecting, setSelecting]     = useState<number | null>(null);
  const [error, setError]             = useState("");

  const [form, setForm] = useState({
    mission_name: "", mission_type: "attack", threat_level: "medium",
    terrain_type: "general", required_team_size: 9, duration_hours: 24,
    description: "",
  });

  useEffect(() => {
    api.get<Mission[]>("/api/v1/missions").then(setMissions).finally(() => setLoading(false));
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const m = await api.post<Mission>("/api/v1/missions", form);
      setMissions(prev => [m, ...prev]);
      setShowNew(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  async function handleOptimize(missionId: number) {
    setOptimizing(missionId);
    setError("");
    try {
      const res = await api.post<{ compositions: TeamComposition[] }>(
        `/api/v1/missions/${missionId}/optimize-team`, {}
      );
      setMissions(prev => prev.map(m =>
        m.id === missionId ? { ...m, compositions: res.compositions } : m
      ));
      setExpanded(missionId);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Optimization failed");
    } finally {
      setOptimizing(null);
    }
  }

  async function handleSelect(missionId: number, compositionId: number) {
    setSelecting(compositionId);
    try {
      await api.post(`/api/v1/missions/${missionId}/select-team/${compositionId}`, {});
      setMissions(prev => prev.map(m => {
        if (m.id !== missionId) return m;
        return {
          ...m,
          status: "active",
          selected_composition_id: compositionId,
          compositions: (m.compositions ?? []).map(c => ({ ...c, is_selected: c.id === compositionId })),
        };
      }));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Select failed");
    } finally {
      setSelecting(null);
    }
  }

  const severityColor: Record<string, string> = {
    low: "text-[#3fb950]", medium: "text-[#f59e0b]", high: "text-[#f85149]", extreme: "text-red-400",
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-black text-white">Team Builder</h1>
          <p className="text-[#8b949e] text-xs mt-0.5">Phase 02 — Team Optimization Engine</p>
        </div>
        <button onClick={() => setShowNew(!showNew)}
          className="flex items-center gap-1.5 px-3 py-2 bg-[#f59e0b] hover:bg-[#d97706] text-black text-sm font-semibold rounded-md transition-colors">
          <Plus size={14} /> New Mission
        </button>
      </div>

      {error && <div className="p-3 bg-[#f85149]/10 border border-[#f85149]/30 text-[#f85149] text-sm rounded-md">{error}</div>}

      {/* New Mission Form */}
      {showNew && (
        <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Create Mission</h2>
          <form onSubmit={handleCreate} className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-[10px] text-[#8b949e] uppercase tracking-wider mb-1">Mission Name *</label>
              <input required value={form.mission_name}
                onChange={e => setForm(p => ({ ...p, mission_name: e.target.value }))}
                className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none focus:border-[#f59e0b]" />
            </div>
            {[
              { id: "mission_type", label: "Type", opts: MISSION_TYPES },
              { id: "threat_level", label: "Threat", opts: THREAT_LEVELS },
              { id: "terrain_type", label: "Terrain", opts: TERRAIN_TYPES },
            ].map(f => (
              <div key={f.id}>
                <label className="block text-[10px] text-[#8b949e] uppercase tracking-wider mb-1">{f.label}</label>
                <select value={(form as Record<string, unknown>)[f.id] as string}
                  onChange={e => setForm(p => ({ ...p, [f.id]: e.target.value }))}
                  className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none">
                  {f.opts.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
            ))}
            <div>
              <label className="block text-[10px] text-[#8b949e] uppercase tracking-wider mb-1">Team Size</label>
              <input type="number" min={2} max={50} value={form.required_team_size}
                onChange={e => setForm(p => ({ ...p, required_team_size: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none" />
            </div>
            <div className="col-span-2">
              <label className="block text-[10px] text-[#8b949e] uppercase tracking-wider mb-1">Description</label>
              <textarea value={form.description} rows={2}
                onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
                className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none resize-none" />
            </div>
            <div className="col-span-2 flex gap-2">
              <button type="submit"
                className="px-4 py-2 bg-[#f59e0b] text-black text-sm font-semibold rounded-md">Save</button>
              <button type="button" onClick={() => setShowNew(false)}
                className="px-4 py-2 bg-[#21262d] text-[#8b949e] text-sm rounded-md hover:text-white">Cancel</button>
            </div>
          </form>
        </div>
      )}

      {/* Missions List */}
      {loading ? (
        <div className="text-[#8b949e] text-sm">Loading missions…</div>
      ) : missions.length === 0 ? (
        <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-8 text-center text-[#8b949e] text-sm">
          No missions yet. Create one to start team optimization.
        </div>
      ) : (
        <div className="space-y-3">
          {missions.map(mission => (
            <div key={mission.id} className="bg-[#161b22] border border-[#30363d] rounded-lg overflow-hidden">
              {/* Mission Header */}
              <div className="px-5 py-4 flex items-center gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-white font-semibold">{mission.mission_name}</h3>
                    <span className={`text-[10px] font-bold uppercase ${severityColor[mission.threat_level] ?? "text-[#8b949e]"}`}>
                      {mission.threat_level} threat
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      mission.status === "active" ? "bg-[#3fb950]/20 text-[#3fb950]" :
                      mission.status === "planning" ? "bg-[#f59e0b]/20 text-[#f59e0b]" :
                      "bg-[#30363d] text-[#8b949e]"
                    }`}>{mission.status}</span>
                    {mission.selected_composition_id && (
                      <CheckCircle size={14} className="text-[#3fb950]" />
                    )}
                  </div>
                  <p className="text-[10px] text-[#8b949e] capitalize">
                    {mission.mission_type} · {mission.terrain_type} · {mission.required_team_size}-person team
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleOptimize(mission.id)}
                    disabled={optimizing === mission.id}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-[#f59e0b] hover:bg-[#d97706] text-black text-xs font-semibold rounded-md transition-colors disabled:opacity-50"
                  >
                    <Zap size={12} />
                    {optimizing === mission.id ? "Optimizing…" : "Optimize Team"}
                  </button>
                  {(mission.compositions?.length ?? 0) > 0 && (
                    <button onClick={() => setExpanded(expanded === mission.id ? null : mission.id)}
                      className="p-1.5 text-[#8b949e] hover:text-white">
                      {expanded === mission.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                  )}
                </div>
              </div>

              {/* Team Options */}
              {expanded === mission.id && (mission.compositions?.length ?? 0) > 0 && (
                <div className="border-t border-[#30363d] divide-y divide-[#30363d]">
                  {(mission.compositions ?? []).sort((a, b) => a.composition_rank - b.composition_rank).map(comp => (
                    <div key={comp.id} className={`px-5 py-4 ${comp.is_selected ? "bg-[#3fb950]/5" : ""}`}>
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-[#8b949e]">Option {comp.composition_rank}</span>
                          {comp.is_selected && (
                            <span className="text-[10px] px-2 py-0.5 bg-[#3fb950]/20 text-[#3fb950] rounded-full font-bold">
                              COMMANDER SELECTED
                            </span>
                          )}
                        </div>
                        {!comp.is_selected && !mission.selected_composition_id && (
                          <button
                            onClick={() => handleSelect(mission.id, comp.id)}
                            disabled={selecting === comp.id}
                            className="text-xs px-3 py-1.5 bg-[#3fb950] hover:bg-green-600 text-black font-semibold rounded-md disabled:opacity-50"
                          >
                            {selecting === comp.id ? "Selecting…" : "Select This Team"}
                          </button>
                        )}
                      </div>

                      <div className="mb-3">
                        <div className="flex items-center justify-between text-[10px] text-[#8b949e] mb-1">
                          <span>Team Fit Score</span>
                        </div>
                        <FitBar score={comp.fit_score} />
                      </div>

                      <p className="text-xs text-[#8b949e] leading-relaxed mb-3 italic">
                        "{comp.rationale}"
                      </p>

                      <div className="grid grid-cols-2 gap-2">
                        {comp.members.map(m => (
                          <div key={m.id} className="flex items-center justify-between bg-[#0d1117] rounded px-3 py-2">
                            <div>
                              <span className="text-xs text-white">{m.name}</span>
                              <span className="ml-2 text-[10px] text-[#8b949e] capitalize">{m.role}</span>
                            </div>
                            <span className="text-[10px] text-[#f59e0b]">{Math.round(m.fit_score * 100)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
