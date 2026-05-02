"use client";
import { useEffect, useRef, useState } from "react";
import { Camera, FileText, Mic, Upload } from "lucide-react";
import { api } from "@/lib/api";
import type { Assessment, Soldier, TrainingEvent } from "@/types";

type Mode = "manual" | "ocr" | "stt";

export default function AssessPage() {
  const [mode, setMode]           = useState<Mode>("manual");
  const [soldiers, setSoldiers]   = useState<Soldier[]>([]);
  const [events, setEvents]       = useState<TrainingEvent[]>([]);
  const [soldierIdStr, setSoldierIdStr] = useState("");
  const [eventIdStr, setEventIdStr]     = useState("");
  const [notes, setNotes]         = useState("");
  const [file, setFile]           = useState<File | null>(null);
  const [loading, setLoading]     = useState(false);
  const [result, setResult]       = useState<Assessment | null>(null);
  const [error, setError]         = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    Promise.all([
      api.get<Soldier[]>("/api/v1/soldiers"),
      api.get<TrainingEvent[]>("/api/v1/events"),
    ]).then(([s, e]) => { setSoldiers(s); setEvents(e); });
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    setResult(null);

    const soldierId = parseInt(soldierIdStr);
    if (!soldierId) { setError("Select a soldier"); setLoading(false); return; }

    try {
      if (mode === "manual") {
        const res = await api.post<Assessment>("/api/v1/assessments", {
          soldier_id: soldierId,
          event_id: eventIdStr ? parseInt(eventIdStr) : null,
          assessment_type: "field_eval",
          notes,
          run_ai_scoring: true,
        });
        setResult(res);
      } else {
        if (!file) { setError("Select a file to upload"); setLoading(false); return; }
        const form = new FormData();
        form.append("soldier_id", String(soldierId));
        if (eventIdStr) form.append("event_id", eventIdStr);
        form.append("assessment_type", "field_eval");
        form.append("file", file);

        const endpoint = mode === "ocr"
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

  const MODES: { key: Mode; label: string; icon: React.ReactNode; desc: string }[] = [
    { key: "manual", label: "Manual Entry", icon: <FileText size={16} />, desc: "Type field notes — AI scores automatically" },
    { key: "ocr",    label: "Photo / OCR",  icon: <Camera size={16} />,   desc: "Upload photo of whiteboard or eval form" },
    { key: "stt",    label: "Voice / STT",  icon: <Mic size={16} />,      desc: "Upload audio recording for transcription" },
  ];

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-black text-white">New Assessment</h1>
        <p className="text-[#8b949e] text-xs mt-0.5">Phase 01 — Data Capture · AI Scoring</p>
      </div>

      {/* Mode selector */}
      <div className="grid grid-cols-3 gap-3">
        {MODES.map(m => (
          <button
            key={m.key}
            onClick={() => { setMode(m.key); setResult(null); setFile(null); setError(""); }}
            className={`p-4 rounded-lg border text-left transition-colors ${
              mode === m.key
                ? "border-[#3fb950] bg-[#3fb950]/10"
                : "border-[#30363d] bg-[#161b22] hover:border-[#8b949e]"
            }`}
          >
            <div className={`mb-2 ${mode === m.key ? "text-[#3fb950]" : "text-[#8b949e]"}`}>{m.icon}</div>
            <div className="text-sm font-semibold text-white">{m.label}</div>
            <div className="text-[10px] text-[#8b949e] mt-0.5">{m.desc}</div>
          </button>
        ))}
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-[#161b22] border border-[#30363d] rounded-lg p-5 space-y-4">
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

        {mode === "manual" && (
          <div>
            <label className="block text-[10px] text-[#8b949e] uppercase tracking-wider mb-1">
              Field Notes / Observations *
            </label>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              required
              rows={6}
              placeholder="Describe the soldier's performance, decisions, leadership behavior, stress response, communication style, tactical choices…"
              className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white placeholder-[#4a5568] focus:outline-none focus:border-[#3fb950] resize-none"
            />
          </div>
        )}

        {(mode === "ocr" || mode === "stt") && (
          <div>
            <label className="block text-[10px] text-[#8b949e] uppercase tracking-wider mb-1">
              {mode === "ocr" ? "Photo (JPEG / PNG)" : "Audio (M4A / MP3 / WAV)"} *
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
              accept={mode === "ocr" ? "image/*" : "audio/*"}
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

      {/* AI Result */}
      {result && (
        <div className="bg-[#161b22] border border-[#3fb950] rounded-lg p-5 space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[#3fb950]" />
            <h2 className="text-sm font-semibold text-white">AI Analysis Complete</h2>
          </div>

          {result.ai_summary && (
            <p className="text-sm text-[#8b949e] leading-relaxed border-l-2 border-[#3fb950] pl-3">
              {result.ai_summary}
            </p>
          )}

          {result.score_leadership != null && (
            <div className="grid grid-cols-5 gap-3">
              {[
                { l: "Leadership", v: result.score_leadership, c: "#3fb950" },
                { l: "Decision",   v: result.score_decision_quality, c: "#f59e0b" },
                { l: "Stress Res.", v: result.score_stress_response, c: "#58a6ff" },
                { l: "Tactical",   v: result.score_tactical, c: "#f85149" },
                { l: "Comms",      v: result.score_communication, c: "#a371f7" },
              ].map(s => s.v != null && (
                <div key={s.l} className="bg-[#0d1117] rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold" style={{ color: s.c }}>
                    {s.v.toFixed(1)}
                  </div>
                  <div className="text-[10px] text-[#8b949e] mt-0.5">{s.l}</div>
                  <div className="text-[10px] text-[#6e7681]">/ 5.0</div>
                </div>
              ))}
            </div>
          )}

          {result.ai_detail && Array.isArray((result.ai_detail as Record<string, unknown>).leadership_traits) && (
            <div>
              <p className="text-[10px] text-[#8b949e] uppercase tracking-wider mb-2">Identified Traits</p>
              <div className="flex flex-wrap gap-2">
                {((result.ai_detail as Record<string, string[]>).leadership_traits).map((t: string) => (
                  <span key={t} className="px-2 py-0.5 bg-[#f59e0b]/10 text-[#f59e0b] text-xs rounded-full capitalize">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {result.raw_capture && (
            <details className="text-xs">
              <summary className="text-[#8b949e] cursor-pointer hover:text-white">
                Raw captured text
              </summary>
              <pre className="mt-2 p-3 bg-[#0d1117] rounded text-[#8b949e] whitespace-pre-wrap text-[11px] leading-relaxed">
                {result.raw_capture}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
