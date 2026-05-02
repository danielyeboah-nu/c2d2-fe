"use client";
import { useEffect, useRef, useState } from "react";
import { Camera, CheckCircle, ChevronDown, ChevronRight, FileText, Mic, Upload } from "lucide-react";
import { api } from "@/lib/api";
import type { Assessment, Soldier, TrainingEvent } from "@/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
type CaptureMode = "structured" | "ocr" | "stt";
type EvalCategory = "leader_eval" | "unit_eval" | "steo_eval";
type Rating = "T" | "P" | "U";

interface Subtask {
  number: number;
  description: string;
}
interface TaskGroup {
  task_group: string;
  subtasks: Subtask[];
}
interface SteoMission {
  mission: string;
  subtasks: Subtask[];
}

const RATING_COLORS: Record<Rating, string> = {
  T: "bg-[#3fb950] text-black border-[#3fb950]",
  P: "bg-[#f59e0b] text-black border-[#f59e0b]",
  U: "bg-[#f85149] text-white border-[#f85149]",
};
const RATING_EMPTY = "bg-transparent text-[#8b949e] border-[#30363d] hover:border-[#8b949e]";

const CATEGORY_LABELS: Record<EvalCategory, string> = {
  leader_eval: "Leader Evaluation",
  unit_eval:   "Unit Evaluation",
  steo_eval:   "SQD ST&EO",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function AssessPage() {
  const [captureMode, setCaptureMode] = useState<CaptureMode>("structured");
  const [evalCategory, setEvalCategory] = useState<EvalCategory>("leader_eval");

  const [soldiers, setSoldiers] = useState<Soldier[]>([]);
  const [events, setEvents]     = useState<TrainingEvent[]>([]);
  const [soldierIdStr, setSoldierIdStr] = useState("");
  const [eventIdStr, setEventIdStr]     = useState("");
  const [notes, setNotes]   = useState("");
  const [file, setFile]     = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Reference rubric data
  const [leaderRef, setLeaderRef] = useState<TaskGroup[]>([]);
  const [unitRef, setUnitRef]     = useState<TaskGroup[]>([]);
  const [steoRef, setSteoRef]     = useState<SteoMission[]>([]);
  const [steoMission, setSteoMission] = useState("");

  // T/P/U ratings keyed by `${evalType}_${taskGroup}_${subtaskNumber}`
  const [ratings, setRatings] = useState<Record<string, Rating>>({});

  // Collapsed state per task group
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState<Assessment | null>(null);
  const [catScores, setCatScores] = useState<Record<string, number> | null>(null);
  const [error, setError]       = useState("");

  // Load soldiers, events, reference data
  useEffect(() => {
    Promise.all([
      api.get<Soldier[]>("/api/v1/soldiers"),
      api.get<TrainingEvent[]>("/api/v1/events"),
      api.get<TaskGroup[]>("/api/v1/analysis/reference/leader"),
      api.get<TaskGroup[]>("/api/v1/analysis/reference/unit"),
      api.get<SteoMission[]>("/api/v1/analysis/reference/steo"),
    ]).then(([s, e, lr, ur, sr]) => {
      setSoldiers(s);
      setEvents(e);
      setLeaderRef(lr);
      setUnitRef(ur);
      setSteoRef(sr);
      if (sr.length) setSteoMission(sr[0].mission);
    });
  }, []);

  function setRating(key: string, r: Rating) {
    setRatings(prev => ({ ...prev, [key]: r }));
  }

  function ratingKey(taskGroup: string, subtaskNum: number) {
    return `${taskGroup}__${subtaskNum}`;
  }

  function buildRatingsPayload(ref: TaskGroup[], evalType: string) {
    return ref.flatMap(group =>
      group.subtasks.map(sub => ({
        task_group: group.task_group,
        task_name: evalType,
        subtask_number: sub.number,
        subtask_description: sub.description,
        rating: ratings[ratingKey(group.task_group, sub.number)] ?? "P",
      }))
    );
  }

  function buildSteoPayload() {
    const mission = steoRef.find(m => m.mission === steoMission);
    if (!mission) return [];
    return mission.subtasks.map(sub => ({
      task_group: "Mission Steps",
      task_name: steoMission,
      subtask_number: sub.number,
      subtask_description: sub.description,
      rating: ratings[ratingKey(steoMission, sub.number)] ?? "P",
    }));
  }

  function completionPct(ref: TaskGroup[] | SteoMission["subtasks"], isSteo = false): number {
    let total = 0; let rated = 0;
    if (isSteo) {
      const mission = steoRef.find(m => m.mission === steoMission);
      if (!mission) return 0;
      mission.subtasks.forEach(sub => {
        total++;
        if (ratings[ratingKey(steoMission, sub.number)]) rated++;
      });
    } else {
      (ref as TaskGroup[]).forEach(g =>
        g.subtasks.forEach(sub => {
          total++;
          if (ratings[ratingKey(g.task_group, sub.number)]) rated++;
        })
      );
    }
    return total ? Math.round((rated / total) * 100) : 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setLoading(true); setResult(null); setCatScores(null);

    const soldierId = parseInt(soldierIdStr);
    if (!soldierId) { setError("Select a soldier"); setLoading(false); return; }

    try {
      if (captureMode === "structured") {
        const payload = {
          soldier_id: soldierId,
          event_id: eventIdStr ? parseInt(eventIdStr) : null,
          eval_category: evalCategory,
          steo_mission_name: evalCategory === "steo_eval" ? steoMission : null,
          leader_ratings: evalCategory === "leader_eval" ? buildRatingsPayload(leaderRef, "Leader Eval") : [],
          unit_ratings:   evalCategory === "unit_eval"   ? buildRatingsPayload(unitRef,   "Unit Eval")   : [],
          steo_ratings:   evalCategory === "steo_eval"   ? buildSteoPayload()                             : [],
          notes,
          run_ai_scoring: !!notes.trim(),
        };
        const res = await api.post<Assessment & { category_scores: Record<string, number> }>(
          "/api/v1/assessments/submit-structured", payload
        );
        setResult(res);
        setCatScores((res as typeof res & { category_scores: Record<string, number> }).category_scores ?? null);
      } else {
        if (!file) { setError("Select a file to upload"); setLoading(false); return; }
        const form = new FormData();
        form.append("soldier_id", String(soldierId));
        if (eventIdStr) form.append("event_id", eventIdStr);
        form.append("assessment_type", "field_eval");
        form.append("file", file);
        const endpoint = captureMode === "ocr"
          ? "/api/v1/assessments/capture/ocr"
          : "/api/v1/assessments/capture/stt";
        const res = await api.upload<Assessment>(endpoint, form);
        setResult(res);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setLoading(false);
    }
  }

  // -------------------------------------------------------------------------
  // Render helpers
  // -------------------------------------------------------------------------
  function RatingButton({ groupKey, sub }: { groupKey: string; sub: Subtask }) {
    const key = ratingKey(groupKey, sub.number);
    const current = ratings[key];
    return (
      <div className="flex items-start gap-3 py-2 border-b border-[#21262d] last:border-0">
        <span className="text-[11px] text-[#8b949e] w-4 text-right flex-shrink-0 mt-0.5">{sub.number}.</span>
        <span className="flex-1 text-xs text-[#c9d1d9]">{sub.description}</span>
        <div className="flex gap-1 flex-shrink-0">
          {(["T", "P", "U"] as Rating[]).map(r => (
            <button
              key={r}
              type="button"
              onClick={() => setRating(key, r)}
              className={`w-8 h-7 rounded text-[11px] font-bold border transition-all ${
                current === r ? RATING_COLORS[r] : RATING_EMPTY
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>
    );
  }

  function TaskGroupSection({ group }: { group: TaskGroup }) {
    const key = group.task_group;
    const isOpen = !collapsed[key];
    const rated = group.subtasks.filter(s => ratings[ratingKey(key, s.number)]).length;
    const all = group.subtasks.length;

    return (
      <div className="border border-[#30363d] rounded-lg overflow-hidden">
        <button
          type="button"
          onClick={() => setCollapsed(prev => ({ ...prev, [key]: !prev[key] }))}
          className="w-full flex items-center justify-between px-4 py-3 bg-[#161b22] hover:bg-[#21262d] transition-colors"
        >
          <div className="flex items-center gap-2">
            {isOpen ? <ChevronDown size={14} className="text-[#8b949e]" /> : <ChevronRight size={14} className="text-[#8b949e]" />}
            <span className="text-sm font-semibold text-white">{key}</span>
          </div>
          <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
            rated === all ? "bg-[#3fb950]/20 text-[#3fb950]" : "bg-[#30363d] text-[#8b949e]"
          }`}>
            {rated}/{all}
          </span>
        </button>
        {isOpen && (
          <div className="px-4 py-1 bg-[#0d1117]">
            {group.subtasks.map(sub => (
              <RatingButton key={sub.number} groupKey={key} sub={sub} />
            ))}
          </div>
        )}
      </div>
    );
  }

  const activeRef = evalCategory === "leader_eval" ? leaderRef : unitRef;
  const pct = captureMode === "structured"
    ? (evalCategory === "steo_eval" ? completionPct([], true) : completionPct(activeRef))
    : 100;

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div>
        <h1 className="text-xl font-black text-white">New Evaluation</h1>
        <p className="text-[#8b949e] text-xs mt-0.5">Phase 01 — Data Capture · AI Scoring</p>
      </div>

      {/* Capture mode */}
      <div className="grid grid-cols-3 gap-3">
        {([
          { key: "structured" as CaptureMode, label: "Structured Eval", icon: <FileText size={16} />, desc: "Leader / Unit / SQD ST&EO rubric" },
          { key: "ocr"        as CaptureMode, label: "Photo / OCR",     icon: <Camera size={16} />,   desc: "Upload photo of whiteboard or form" },
          { key: "stt"        as CaptureMode, label: "Voice / STT",     icon: <Mic size={16} />,      desc: "Upload audio for transcription" },
        ]).map(m => (
          <button
            key={m.key}
            onClick={() => { setCaptureMode(m.key); setResult(null); setError(""); }}
            className={`p-4 rounded-lg border text-left transition-colors ${
              captureMode === m.key ? "border-[#3fb950] bg-[#3fb950]/10" : "border-[#30363d] bg-[#161b22] hover:border-[#8b949e]"
            }`}
          >
            <div className={`mb-2 ${captureMode === m.key ? "text-[#3fb950]" : "text-[#8b949e]"}`}>{m.icon}</div>
            <div className="text-sm font-semibold text-white">{m.label}</div>
            <div className="text-[10px] text-[#8b949e] mt-0.5">{m.desc}</div>
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Soldier + Event */}
        <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[10px] text-[#8b949e] uppercase tracking-wider mb-1">Soldier *</label>
              <select
                value={soldierIdStr}
                onChange={e => setSoldierIdStr(e.target.value)}
                required
                className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none focus:border-[#3fb950]"
              >
                <option value="">Select soldier…</option>
                {soldiers.map(s => (
                  <option key={s.id} value={String(s.id)}>{s.rank} {s.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[10px] text-[#8b949e] uppercase tracking-wider mb-1">Training Event</label>
              <select
                value={eventIdStr}
                onChange={e => setEventIdStr(e.target.value)}
                className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none focus:border-[#3fb950]"
              >
                <option value="">None</option>
                {events.map(ev => (
                  <option key={ev.id} value={String(ev.id)}>{ev.event_name}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Structured eval */}
        {captureMode === "structured" && (
          <div className="space-y-4">
            {/* Eval type tabs */}
            <div className="flex gap-1 bg-[#161b22] border border-[#30363d] rounded-lg p-1">
              {(["leader_eval", "unit_eval", "steo_eval"] as EvalCategory[]).map(cat => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => { setEvalCategory(cat); setRatings({}); setCollapsed({}); }}
                  className={`flex-1 py-2 rounded-md text-sm font-semibold transition-colors ${
                    evalCategory === cat
                      ? "bg-[#3fb950] text-black"
                      : "text-[#8b949e] hover:text-white"
                  }`}
                >
                  {CATEGORY_LABELS[cat]}
                </button>
              ))}
            </div>

            {/* Progress bar */}
            <div className="flex items-center gap-3">
              <div className="flex-1 h-1.5 bg-[#21262d] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#3fb950] transition-all duration-300"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-[11px] text-[#8b949e] w-10 text-right">{pct}%</span>
            </div>

            {/* Rating legend */}
            <div className="flex gap-4 text-[11px]">
              <span className="text-[#3fb950] font-bold">T</span><span className="text-[#8b949e]">= Trained (5)</span>
              <span className="text-[#f59e0b] font-bold ml-2">P</span><span className="text-[#8b949e]">= Partially Trained (3)</span>
              <span className="text-[#f85149] font-bold ml-2">U</span><span className="text-[#8b949e]">= Untrained (1)</span>
            </div>

            {/* Leader / Unit eval — category sections */}
            {(evalCategory === "leader_eval" || evalCategory === "unit_eval") && (
              <div className="space-y-2">
                {activeRef.map(group => (
                  <TaskGroupSection key={group.task_group} group={group} />
                ))}
              </div>
            )}

            {/* ST&EO eval */}
            {evalCategory === "steo_eval" && (
              <div className="space-y-3">
                <div>
                  <label className="block text-[10px] text-[#8b949e] uppercase tracking-wider mb-1">Mission Type *</label>
                  <select
                    value={steoMission}
                    onChange={e => { setSteoMission(e.target.value); setRatings({}); }}
                    className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:outline-none focus:border-[#3fb950]"
                  >
                    {steoRef.map(m => (
                      <option key={m.mission} value={m.mission}>{m.mission}</option>
                    ))}
                  </select>
                </div>
                <div className="border border-[#30363d] rounded-lg overflow-hidden">
                  <div className="px-4 py-2 bg-[#161b22] text-xs font-semibold text-[#8b949e] uppercase tracking-wider">
                    Steps — Rate each T / P / U
                  </div>
                  <div className="px-4 py-1 bg-[#0d1117]">
                    {steoRef.find(m => m.mission === steoMission)?.subtasks.map(sub => (
                      <RatingButton key={sub.number} groupKey={steoMission} sub={sub} />
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Optional notes */}
            <div>
              <label className="block text-[10px] text-[#8b949e] uppercase tracking-wider mb-1">
                Evaluator Notes <span className="normal-case">(optional — triggers AI scoring)</span>
              </label>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                rows={3}
                placeholder="Additional observations, context, or freeform notes…"
                className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white placeholder-[#4a5568] focus:outline-none focus:border-[#3fb950] resize-none"
              />
            </div>
          </div>
        )}

        {/* OCR / STT upload */}
        {(captureMode === "ocr" || captureMode === "stt") && (
          <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-4 space-y-3">
            <label className="block text-[10px] text-[#8b949e] uppercase tracking-wider">
              {captureMode === "ocr" ? "Photo (JPEG / PNG)" : "Audio (M4A / MP3 / WAV)"} *
            </label>
            <div
              onClick={() => fileRef.current?.click()}
              className="border-2 border-dashed border-[#30363d] rounded-lg p-8 text-center cursor-pointer hover:border-[#3fb950] transition-colors"
            >
              <Upload size={24} className="mx-auto text-[#8b949e] mb-2" />
              {file ? (
                <p className="text-sm text-[#3fb950]">{file.name}</p>
              ) : (
                <p className="text-sm text-[#8b949e]">Click to select file</p>
              )}
            </div>
            <input
              ref={fileRef}
              type="file"
              accept={captureMode === "ocr" ? "image/*" : "audio/*"}
              className="hidden"
              onChange={e => setFile(e.target.files?.[0] ?? null)}
            />
          </div>
        )}

        {error && <p className="text-[#f85149] text-xs">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 bg-[#3fb950] hover:bg-green-600 text-black font-bold text-sm rounded-md transition-colors disabled:opacity-50"
        >
          {loading ? "Processing…" : "Submit & Score"}
        </button>
      </form>

      {/* Result */}
      {result && (
        <div className="bg-[#161b22] border border-[#3fb950] rounded-lg p-5 space-y-4">
          <div className="flex items-center gap-2">
            <CheckCircle size={16} className="text-[#3fb950]" />
            <h2 className="text-sm font-semibold text-white">Evaluation Recorded</h2>
            {result.eval_category && (
              <span className="ml-auto text-[10px] bg-[#3fb950]/10 text-[#3fb950] px-2 py-0.5 rounded-full uppercase tracking-wider">
                {CATEGORY_LABELS[result.eval_category as EvalCategory]}
              </span>
            )}
          </div>

          {/* Category scores */}
          {catScores && Object.keys(catScores).length > 0 && (
            <div>
              <p className="text-[10px] text-[#8b949e] uppercase tracking-wider mb-2">Category Scores</p>
              <div className="grid grid-cols-5 gap-2">
                {Object.entries(catScores).map(([cat, score]) => {
                  const color = score >= 4.5 ? "#3fb950" : score >= 3 ? "#f59e0b" : "#f85149";
                  const label = score >= 4.5 ? "T" : score >= 3 ? "P" : "U";
                  return (
                    <div key={cat} className="bg-[#0d1117] rounded-lg p-3 text-center">
                      <div className="text-xl font-bold" style={{ color }}>{score.toFixed(1)}</div>
                      <div className="text-[10px] text-[#8b949e] mt-0.5 leading-tight">{cat}</div>
                      <div className="text-[10px] font-bold mt-0.5" style={{ color }}>{label}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* AI scores (when notes were provided) */}
          {result.score_leadership != null && (
            <div>
              <p className="text-[10px] text-[#8b949e] uppercase tracking-wider mb-2">AI Analysis</p>
              <div className="grid grid-cols-5 gap-2">
                {[
                  { l: "Leadership",  v: result.score_leadership,      c: "#3fb950" },
                  { l: "Decision",    v: result.score_decision_quality, c: "#f59e0b" },
                  { l: "Stress Res.", v: result.score_stress_response,  c: "#58a6ff" },
                  { l: "Tactical",    v: result.score_tactical,         c: "#f85149" },
                  { l: "Comms",       v: result.score_communication,    c: "#a371f7" },
                ].map(s => s.v != null && (
                  <div key={s.l} className="bg-[#0d1117] rounded-lg p-3 text-center">
                    <div className="text-xl font-bold" style={{ color: s.c }}>{s.v.toFixed(1)}</div>
                    <div className="text-[10px] text-[#8b949e] mt-0.5">{s.l}</div>
                    <div className="text-[10px] text-[#6e7681]">/ 5.0</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.ai_summary && (
            <p className="text-sm text-[#8b949e] leading-relaxed border-l-2 border-[#3fb950] pl-3">
              {result.ai_summary}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
