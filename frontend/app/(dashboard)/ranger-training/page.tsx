"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import {
  Bot, Send, RefreshCw, CheckCircle, XCircle, AlertTriangle,
  ChevronDown, ChevronRight, Mic, Image, FileText, Clock, Loader2,
} from "lucide-react";

const S1_API = "http://127.0.0.1:8001";

type RunStatus = "accepted" | "processing" | "pending_approval" | "completed" | "failed";

interface Geo { lat: number; lon: number; grid_mgrs: string; }
interface PolicyDecision { allowed: boolean; reasons: string[]; fairness_score?: number; }
interface ScenarioRecommendation {
  recommendation_id: string;
  target_soldier_id?: string;
  rationale: string;
  development_edge?: string;
  learning_objective?: string;
  proposed_modification?: string;
  doctrine_refs?: string[];
  safety_checks?: string[];
  risk_level?: string;
  evidence_refs?: string[];
}
interface RecommendationRecord {
  recommendation: ScenarioRecommendation;
  policy: PolicyDecision;
  status: "pending" | "approved" | "rejected" | "blocked";
}
interface Observation {
  observation_id: string;
  soldier_id?: string;
  task_code?: string;
  note?: string;
  rating: "GO" | "NOGO" | "UNCERTAIN";
  source?: string;
}
interface RunRecord {
  run_id: string;
  status: RunStatus;
  observations?: Observation[];
  recommendations?: RecommendationRecord[];
  errors?: string[];
}
interface SoldierSummary {
  soldier_id: string;
  go_count: number;
  nogo_count: number;
  uncertain_count: number;
  go_rate: number;
  readiness_score: number;
}
interface DashboardSummary {
  run_id: string;
  mission_id?: string;
  status: RunStatus;
  total_observations: number;
  pending_recommendations: number;
  blocked_recommendations: number;
  approved_recommendations: number;
  platoon_readiness_score?: number;
  soldiers?: SoldierSummary[];
}

const PHASES = ["Benning", "Mountain", "Florida"] as const;
const STATUS_LABELS: Record<RunStatus, { label: string; color: string }> = {
  accepted:         { label: "Queued",           color: "text-[#8b949e]" },
  processing:       { label: "Processing",       color: "text-[#f59e0b]" },
  pending_approval: { label: "Awaiting Approval",color: "text-[#58a6ff]" },
  completed:        { label: "Completed",        color: "text-[#3fb950]" },
  failed:           { label: "Failed",           color: "text-[#f85149]" },
};

async function s1Fetch<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${S1_API}${path}`, {
    ...opts,
    headers: { "Content-Type": "application/json", ...(opts?.headers ?? {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body?.detail ?? `Request failed ${res.status}`);
  return body as T;
}

function toBase64(file: File): Promise<string> {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => res((r.result as string).split(",")[1]);
    r.onerror = rej;
    r.readAsDataURL(file);
  });
}

function Badge({ label, color }: { label: string; color: string }) {
  return <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${color}`}>{label}</span>;
}

function RatingBadge({ rating }: { rating: "GO" | "NOGO" | "UNCERTAIN" }) {
  const map = { GO: "bg-[#3fb950]/20 text-[#3fb950]", NOGO: "bg-[#f85149]/20 text-[#f85149]", UNCERTAIN: "bg-[#f59e0b]/20 text-[#f59e0b]" };
  return <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${map[rating]}`}>{rating}</span>;
}

export default function RangerTrainingPage() {
  const [instructorId, setInstructorId] = useState("instructor-1");
  const [platoonId, setPlatoonId]     = useState("plt-1");
  const [missionId, setMissionId]     = useState("mission-mountain-01");
  const [phase, setPhase]             = useState<typeof PHASES[number]>("Mountain");
  const [lat, setLat]                 = useState("35.0");
  const [lon, setLon]                 = useState("-83.0");
  const [grid, setGrid]               = useState("17S");
  const [freeText, setFreeText]       = useState("");
  const [audioFile, setAudioFile]     = useState<File | null>(null);
  const [imageFiles, setImageFiles]   = useState<File[]>([]);
  const [submitting, setSubmitting]   = useState(false);
  const [error, setError]             = useState<string | null>(null);

  const [runId, setRunId]           = useState<string | null>(null);
  const [run, setRun]               = useState<RunRecord | null>(null);
  const [dashboard, setDashboard]   = useState<DashboardSummary | null>(null);
  const [polling, setPolling]       = useState(false);
  const pollRef                     = useRef<ReturnType<typeof setInterval> | null>(null);

  const [deciding, setDeciding]     = useState<string | null>(null);
  const [expandedRec, setExpandedRec] = useState<string | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    setPolling(false);
  }, []);

  const fetchRun = useCallback(async (id: string) => {
    try {
      const r = await s1Fetch<RunRecord>(`/v1/runs/${id}`);
      setRun(r);
      if (["pending_approval", "completed", "failed"].includes(r.status)) {
        stopPolling();
        if (r.status !== "failed") {
          const d = await s1Fetch<DashboardSummary>(`/v1/dashboard/runs/${id}`);
          setDashboard(d);
        }
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to fetch run");
      stopPolling();
    }
  }, [stopPolling]);

  const startPolling = useCallback((id: string) => {
    setPolling(true);
    fetchRun(id);
    pollRef.current = setInterval(() => fetchRun(id), 2000);
  }, [fetchRun]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  async function handleSubmit() {
    if (!freeText && !audioFile && imageFiles.length === 0) {
      setError("Attach at least one evidence source (text, audio, or image).");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const audio_b64 = audioFile ? await toBase64(audioFile) : null;
      const image_b64 = await Promise.all(imageFiles.map(toBase64));
      const result = await s1Fetch<RunRecord>("/v1/ingest", {
        method: "POST",
        body: JSON.stringify({
          instructor_id: instructorId,
          platoon_id: platoonId,
          mission_id: missionId,
          phase,
          timestamp_utc: new Date().toISOString(),
          geo: { lat: parseFloat(lat), lon: parseFloat(lon), grid_mgrs: grid },
          free_text: freeText || null,
          audio_b64,
          image_b64,
        }),
      });
      setRunId(result.run_id);
      setRun(result);
      setDashboard(null);
      startPolling(result.run_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ingest failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDecision(recId: string, decision: "approve" | "reject") {
    setDeciding(recId);
    try {
      await s1Fetch(`/v1/recommendations/${recId}/decision`, {
        method: "POST",
        body: JSON.stringify({ decision }),
      });
      if (runId) await fetchRun(runId);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Decision failed");
    } finally {
      setDeciding(null);
    }
  }

  const statusInfo = run ? STATUS_LABELS[run.status] : null;
  const pending  = run?.recommendations?.filter(r => r.status === "pending")  ?? [];
  const blocked  = run?.recommendations?.filter(r => r.status === "blocked")  ?? [];
  const decided  = run?.recommendations?.filter(r => ["approved","rejected"].includes(r.status)) ?? [];

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#c9d1d9] p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Bot size={24} className="text-[#58a6ff]" />
          <div>
            <h1 className="text-xl font-bold text-white">Ranger AI</h1>
            <p className="text-xs text-[#8b949e]">Adversarial Training Agent — System 1 · {S1_API}</p>
          </div>
          {statusInfo && (
            <div className="ml-auto flex items-center gap-2">
              {polling && <Loader2 size={14} className="animate-spin text-[#f59e0b]" />}
              <span className={`text-sm font-semibold ${statusInfo.color}`}>{statusInfo.label}</span>
            </div>
          )}
        </div>

        {error && (
          <div className="mb-4 p-3 bg-[#f85149]/10 border border-[#f85149]/30 rounded-lg text-sm text-[#f85149] flex items-center gap-2">
            <AlertTriangle size={14} /> {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Left: Ingest Form */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-4">
              <h2 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                <Send size={14} className="text-[#58a6ff]" /> Evidence Ingest
              </h2>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-[#8b949e] uppercase tracking-wider">Instructor ID</label>
                    <input value={instructorId} onChange={e => setInstructorId(e.target.value)}
                      className="mt-1 w-full bg-[#0d1117] border border-[#30363d] rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-[#58a6ff]" />
                  </div>
                  <div>
                    <label className="text-[10px] text-[#8b949e] uppercase tracking-wider">Platoon ID</label>
                    <input value={platoonId} onChange={e => setPlatoonId(e.target.value)}
                      className="mt-1 w-full bg-[#0d1117] border border-[#30363d] rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-[#58a6ff]" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-[#8b949e] uppercase tracking-wider">Mission ID</label>
                    <input value={missionId} onChange={e => setMissionId(e.target.value)}
                      className="mt-1 w-full bg-[#0d1117] border border-[#30363d] rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-[#58a6ff]" />
                  </div>
                  <div>
                    <label className="text-[10px] text-[#8b949e] uppercase tracking-wider">Phase</label>
                    <select value={phase} onChange={e => setPhase(e.target.value as typeof PHASES[number])}
                      className="mt-1 w-full bg-[#0d1117] border border-[#30363d] rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-[#58a6ff]">
                      {PHASES.map(p => <option key={p}>{p}</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="text-[10px] text-[#8b949e] uppercase tracking-wider">Lat</label>
                    <input value={lat} onChange={e => setLat(e.target.value)}
                      className="mt-1 w-full bg-[#0d1117] border border-[#30363d] rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-[#58a6ff]" />
                  </div>
                  <div>
                    <label className="text-[10px] text-[#8b949e] uppercase tracking-wider">Lon</label>
                    <input value={lon} onChange={e => setLon(e.target.value)}
                      className="mt-1 w-full bg-[#0d1117] border border-[#30363d] rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-[#58a6ff]" />
                  </div>
                  <div>
                    <label className="text-[10px] text-[#8b949e] uppercase tracking-wider">MGRS Grid</label>
                    <input value={grid} onChange={e => setGrid(e.target.value)}
                      className="mt-1 w-full bg-[#0d1117] border border-[#30363d] rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-[#58a6ff]" />
                  </div>
                </div>
                <div>
                  <label className="text-[10px] text-[#8b949e] uppercase tracking-wider flex items-center gap-1">
                    <FileText size={10} /> Free Text Notes
                  </label>
                  <textarea value={freeText} onChange={e => setFreeText(e.target.value)} rows={4}
                    placeholder="e.g. Jones blew Phase Line Bird. Smith asleep at 0300..."
                    className="mt-1 w-full bg-[#0d1117] border border-[#30363d] rounded px-2 py-1.5 text-xs text-white resize-none focus:outline-none focus:border-[#58a6ff] placeholder-[#6e7681]" />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-[#8b949e] uppercase tracking-wider flex items-center gap-1 mb-1">
                      <Mic size={10} /> Audio (optional)
                    </label>
                    <label className="cursor-pointer flex items-center gap-2 border border-dashed border-[#30363d] rounded px-2 py-2 text-xs text-[#8b949e] hover:border-[#58a6ff] transition-colors">
                      <input type="file" accept="audio/*" className="hidden" onChange={e => setAudioFile(e.target.files?.[0] ?? null)} />
                      {audioFile ? <span className="text-[#3fb950] truncate">{audioFile.name}</span> : "Upload audio"}
                    </label>
                  </div>
                  <div>
                    <label className="text-[10px] text-[#8b949e] uppercase tracking-wider flex items-center gap-1 mb-1">
                      <Image size={10} /> Images (optional)
                    </label>
                    <label className="cursor-pointer flex items-center gap-2 border border-dashed border-[#30363d] rounded px-2 py-2 text-xs text-[#8b949e] hover:border-[#58a6ff] transition-colors">
                      <input type="file" accept="image/*" multiple className="hidden" onChange={e => setImageFiles(Array.from(e.target.files ?? []))} />
                      {imageFiles.length ? <span className="text-[#3fb950]">{imageFiles.length} image(s)</span> : "Upload images"}
                    </label>
                  </div>
                </div>
                <button onClick={handleSubmit} disabled={submitting}
                  className="w-full bg-[#58a6ff] hover:bg-[#58a6ff]/80 disabled:opacity-50 text-[#0d1117] font-bold text-xs py-2 rounded transition-colors flex items-center justify-center gap-2">
                  {submitting ? <><Loader2 size={14} className="animate-spin" /> Submitting...</> : <><Send size={14} /> Submit Ingest</>}
                </button>
              </div>
            </div>

            {/* Run Status */}
            {run && (
              <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-4">
                <h2 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                  <Clock size={14} className="text-[#58a6ff]" /> Run Status
                </h2>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between"><span className="text-[#8b949e]">Run ID</span><span className="font-mono text-[#58a6ff]">{run.run_id.slice(0,16)}…</span></div>
                  <div className="flex justify-between"><span className="text-[#8b949e]">Status</span><span className={statusInfo?.color}>{statusInfo?.label}</span></div>
                  {run.observations && <div className="flex justify-between"><span className="text-[#8b949e]">Observations</span><span className="text-white">{run.observations.length}</span></div>}
                  {run.recommendations && <div className="flex justify-between"><span className="text-[#8b949e]">Recommendations</span><span className="text-white">{run.recommendations.length}</span></div>}
                </div>
                {run.errors?.length ? (
                  <div className="mt-3 p-2 bg-[#f85149]/10 rounded text-xs text-[#f85149]">
                    {run.errors.map((e, i) => <div key={i}>{e}</div>)}
                  </div>
                ) : null}
                {polling && (
                  <div className="mt-3 flex items-center gap-2 text-xs text-[#f59e0b]">
                    <Loader2 size={12} className="animate-spin" /> Polling for updates…
                  </div>
                )}
              </div>
            )}

            {/* Dashboard Summary */}
            {dashboard && (
              <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-4">
                <h2 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                  <RefreshCw size={14} className="text-[#3fb950]" /> Platoon Summary
                </h2>
                <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                  {dashboard.platoon_readiness_score != null && (
                    <div className="col-span-2">
                      <div className="flex justify-between mb-1"><span className="text-[#8b949e]">Platoon Readiness</span><span className="text-[#3fb950] font-bold">{(dashboard.platoon_readiness_score * 100).toFixed(0)}%</span></div>
                      <div className="h-1.5 bg-[#30363d] rounded-full"><div className="h-1.5 bg-[#3fb950] rounded-full transition-all" style={{ width: `${dashboard.platoon_readiness_score * 100}%` }} /></div>
                    </div>
                  )}
                  <div className="bg-[#0d1117] rounded p-2"><div className="text-[#8b949e]">Observations</div><div className="text-white font-bold mt-0.5">{dashboard.total_observations}</div></div>
                  <div className="bg-[#0d1117] rounded p-2"><div className="text-[#8b949e]">Pending</div><div className="text-[#58a6ff] font-bold mt-0.5">{dashboard.pending_recommendations}</div></div>
                  <div className="bg-[#0d1117] rounded p-2"><div className="text-[#8b949e]">Approved</div><div className="text-[#3fb950] font-bold mt-0.5">{dashboard.approved_recommendations}</div></div>
                  <div className="bg-[#0d1117] rounded p-2"><div className="text-[#8b949e]">Blocked</div><div className="text-[#f85149] font-bold mt-0.5">{dashboard.blocked_recommendations}</div></div>
                </div>
                {dashboard.soldiers?.map(s => (
                  <div key={s.soldier_id} className="flex items-center gap-2 py-1.5 border-t border-[#21262d] text-xs">
                    <span className="flex-1 text-[#8b949e] truncate">{s.soldier_id}</span>
                    <span className="text-[#3fb950]">{s.go_count}G</span>
                    <span className="text-[#f85149]">{s.nogo_count}N</span>
                    <span className="text-[#f59e0b] font-bold">{(s.go_rate * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right: Recommendations */}
          <div className="lg:col-span-3 space-y-3">
            {!run && (
              <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-8 text-center">
                <Bot size={40} className="text-[#30363d] mx-auto mb-3" />
                <p className="text-sm text-[#8b949e]">Submit an ingest to see recommendations</p>
              </div>
            )}

            {/* Observations */}
            {(run?.observations?.length ?? 0) > 0 && (
              <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-4">
                <h2 className="text-sm font-bold text-white mb-3">Observations ({run!.observations!.length})</h2>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {run!.observations!.map(o => (
                    <div key={o.observation_id} className="flex items-start gap-2 text-xs py-1.5 border-b border-[#21262d] last:border-0">
                      <RatingBadge rating={o.rating} />
                      <div className="flex-1">
                        {o.soldier_id && <span className="text-[#58a6ff] mr-1">{o.soldier_id}</span>}
                        {o.task_code && <span className="text-[#8b949e] mr-1">[{o.task_code}]</span>}
                        <span className="text-[#c9d1d9]">{o.note}</span>
                      </div>
                      {o.source && <span className="text-[#6e7681] shrink-0">{o.source}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Pending Recommendations */}
            {pending.length > 0 && (
              <div>
                <h2 className="text-xs font-bold text-[#58a6ff] uppercase tracking-wider mb-2">Pending Approval ({pending.length})</h2>
                <div className="space-y-3">
                  {pending.map(({ recommendation: rec, policy }) => {
                    const open = expandedRec === rec.recommendation_id;
                    return (
                      <div key={rec.recommendation_id} className="bg-[#161b22] border border-[#30363d] rounded-lg overflow-hidden">
                        <button onClick={() => setExpandedRec(open ? null : rec.recommendation_id)}
                          className="w-full flex items-start gap-3 p-4 text-left hover:bg-[#21262d] transition-colors">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              {rec.target_soldier_id && <Badge label={rec.target_soldier_id} color="bg-[#58a6ff]/10 text-[#58a6ff]" />}
                              {rec.risk_level && <Badge label={rec.risk_level} color={rec.risk_level === "high" ? "bg-[#f85149]/10 text-[#f85149]" : "bg-[#f59e0b]/10 text-[#f59e0b]"} />}
                            </div>
                            <p className="text-sm text-white leading-snug">{rec.proposed_modification ?? rec.rationale}</p>
                            {rec.development_edge && <p className="text-xs text-[#58a6ff] mt-1">Edge: {rec.development_edge}</p>}
                          </div>
                          {open ? <ChevronDown size={14} className="text-[#8b949e] shrink-0 mt-0.5" /> : <ChevronRight size={14} className="text-[#8b949e] shrink-0 mt-0.5" />}
                        </button>
                        {open && (
                          <div className="px-4 pb-4 space-y-2 text-xs border-t border-[#21262d]">
                            {rec.learning_objective && <p className="text-[#8b949e] pt-2"><span className="text-white">Objective:</span> {rec.learning_objective}</p>}
                            {rec.rationale && <p className="text-[#8b949e]"><span className="text-white">Rationale:</span> {rec.rationale}</p>}
                            {rec.safety_checks?.length ? (
                              <div><span className="text-white">Safety Checks:</span>
                                <ul className="mt-1 space-y-0.5">{rec.safety_checks.map((c, i) => <li key={i} className="text-[#f59e0b] flex gap-1"><AlertTriangle size={10} className="shrink-0 mt-0.5" />{c}</li>)}</ul>
                              </div>
                            ) : null}
                            {rec.doctrine_refs?.length ? (
                              <div><span className="text-white">Doctrine:</span>
                                <ul className="mt-1 space-y-0.5">{rec.doctrine_refs.map((d, i) => <li key={i} className="text-[#8b949e]">• {d}</li>)}</ul>
                              </div>
                            ) : null}
                          </div>
                        )}
                        <div className="flex gap-2 px-4 py-3 bg-[#0d1117] border-t border-[#21262d]">
                          <button onClick={() => handleDecision(rec.recommendation_id, "approve")}
                            disabled={deciding === rec.recommendation_id}
                            className="flex-1 flex items-center justify-center gap-1.5 bg-[#3fb950]/10 hover:bg-[#3fb950]/20 border border-[#3fb950]/30 text-[#3fb950] text-xs font-bold py-1.5 rounded transition-colors disabled:opacity-50">
                            {deciding === rec.recommendation_id ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle size={12} />} Approve
                          </button>
                          <button onClick={() => handleDecision(rec.recommendation_id, "reject")}
                            disabled={deciding === rec.recommendation_id}
                            className="flex-1 flex items-center justify-center gap-1.5 bg-[#f85149]/10 hover:bg-[#f85149]/20 border border-[#f85149]/30 text-[#f85149] text-xs font-bold py-1.5 rounded transition-colors disabled:opacity-50">
                            <XCircle size={12} /> Reject
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Blocked */}
            {blocked.length > 0 && (
              <div>
                <h2 className="text-xs font-bold text-[#f85149] uppercase tracking-wider mb-2">Blocked ({blocked.length})</h2>
                <div className="space-y-2">
                  {blocked.map(({ recommendation: rec, policy }) => (
                    <div key={rec.recommendation_id} className="bg-[#161b22] border border-[#f85149]/20 rounded-lg p-4 opacity-75">
                      <p className="text-sm text-white mb-2">{rec.proposed_modification ?? rec.rationale}</p>
                      <div className="space-y-1">
                        {policy.reasons.map((r, i) => (
                          <div key={i} className="flex items-center gap-1.5 text-xs text-[#f85149]"><XCircle size={10} /> {r}</div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Decided */}
            {decided.length > 0 && (
              <div>
                <h2 className="text-xs font-bold text-[#8b949e] uppercase tracking-wider mb-2">Decided ({decided.length})</h2>
                <div className="space-y-2">
                  {decided.map(({ recommendation: rec, status }) => (
                    <div key={rec.recommendation_id} className="bg-[#161b22] border border-[#30363d] rounded-lg p-3 flex items-start gap-3 opacity-60">
                      {status === "approved"
                        ? <CheckCircle size={14} className="text-[#3fb950] shrink-0 mt-0.5" />
                        : <XCircle size={14} className="text-[#f85149] shrink-0 mt-0.5" />}
                      <p className="text-xs text-[#8b949e]">{rec.proposed_modification ?? rec.rationale}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
