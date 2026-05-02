"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip,
  LineChart, Line, XAxis, YAxis, CartesianGrid
} from "recharts";
import { api } from "@/lib/api";
import type { Assessment, Soldier } from "@/types";

const RADAR_DIMS = [
  { key: "leadership",       label: "Leadership" },
  { key: "decision_making",  label: "Decision" },
  { key: "stress_tolerance", label: "Stress" },
  { key: "tactical",         label: "Tactical" },
  { key: "communication",    label: "Comms" },
  { key: "teamwork",         label: "Teamwork" },
  { key: "adaptability",     label: "Adapt" },
];

export default function SoldierDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router  = useRouter();
  const [soldier, setSoldier]       = useState<Soldier | null>(null);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading]       = useState(true);

  useEffect(() => {
    Promise.all([
      api.get<Soldier>(`/api/v1/soldiers/${id}`),
      api.get<Assessment[]>(`/api/v1/soldiers/${id}/assessments`),
    ]).then(([s, a]) => {
      setSoldier(s);
      setAssessments(a);
    }).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-6 text-[#8b949e]">Loading…</div>;
  if (!soldier) return <div className="p-6 text-[#f85149]">Soldier not found</div>;

  const radarData = RADAR_DIMS.map(d => ({
    subject: d.label,
    score: Math.round((soldier.skill_vector[d.key as keyof typeof soldier.skill_vector] ?? 0.5) * 100),
    fullMark: 100,
  }));

  const trendData = assessments
    .filter(a => a.score_leadership != null)
    .slice(0, 10)
    .reverse()
    .map((a, i) => ({
      label: `#${i + 1}`,
      leadership: a.score_leadership,
      decision: a.score_decision_quality,
      stress: a.score_stress_response,
      tactical: a.score_tactical,
    }));

  return (
    <div className="p-6 space-y-6">
      {/* Back + Header */}
      <div>
        <button onClick={() => router.back()} className="flex items-center gap-1 text-xs text-[#8b949e] hover:text-white mb-3">
          <ArrowLeft size={14} /> Back
        </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-black text-white">{soldier.rank} {soldier.name}</h1>
            <p className="text-[#8b949e] text-sm">{soldier.unit} · {soldier.mos} · {soldier.service_number}</p>
          </div>
          <div className="flex gap-2">
            <span className={`text-xs px-2 py-1 rounded ${soldier.is_active ? "bg-[#3fb950]/20 text-[#3fb950]" : "bg-[#30363d] text-[#8b949e]"}`}>
              {soldier.is_active ? "Active" : "Inactive"}
            </span>
            <span className="text-xs px-2 py-1 bg-[#21262d] text-[#8b949e] rounded capitalize">
              {soldier.decision_style}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Radar */}
        <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Skill Profile</h2>
          <ResponsiveContainer width="100%" height={260}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#30363d" />
              <PolarAngleAxis dataKey="subject" tick={{ fill: "#8b949e", fontSize: 11 }} />
              <Radar name={soldier.name} dataKey="score" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.2} />
              <Tooltip
                contentStyle={{ backgroundColor: "#161b22", border: "1px solid #30363d", borderRadius: "6px" }}
                labelStyle={{ color: "#e6edf3" }}
                itemStyle={{ color: "#f59e0b" }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Performance Trend */}
        <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
          <h2 className="text-sm font-semibold text-white mb-4">
            Assessment Trend ({assessments.length} evals)
          </h2>
          {trendData.length === 0 ? (
            <div className="h-[260px] flex items-center justify-center text-[#8b949e] text-sm">
              No scored assessments yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                <XAxis dataKey="label" tick={{ fill: "#8b949e", fontSize: 10 }} />
                <YAxis domain={[0, 5]} tick={{ fill: "#8b949e", fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#161b22", border: "1px solid #30363d", borderRadius: "6px" }}
                  labelStyle={{ color: "#e6edf3" }}
                />
                <Line type="monotone" dataKey="leadership" stroke="#3fb950" strokeWidth={2} dot={false} name="Leadership" />
                <Line type="monotone" dataKey="decision" stroke="#f59e0b" strokeWidth={2} dot={false} name="Decision" />
                <Line type="monotone" dataKey="stress" stroke="#58a6ff" strokeWidth={2} dot={false} name="Stress Res." />
                <Line type="monotone" dataKey="tactical" stroke="#f85149" strokeWidth={2} dot={false} name="Tactical" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Traits + Style */}
      {soldier.leadership_traits.length > 0 && (
        <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
          <h2 className="text-sm font-semibold text-white mb-3">Leadership Traits</h2>
          <div className="flex flex-wrap gap-2">
            {soldier.leadership_traits.map(t => (
              <span key={t} className="px-2.5 py-1 bg-[#f59e0b]/10 text-[#f59e0b] text-xs rounded-full capitalize">
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Assessment History */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg">
        <div className="px-5 py-4 border-b border-[#30363d]">
          <h2 className="text-sm font-semibold text-white">Assessment History</h2>
        </div>
        {assessments.length === 0 ? (
          <div className="px-5 py-8 text-center text-[#8b949e] text-sm">No assessments recorded</div>
        ) : (
          <div className="divide-y divide-[#30363d]">
            {assessments.map(a => (
              <div key={a.id} className="px-5 py-4">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <span className="text-xs text-white capitalize">{a.assessment_type.replace(/_/g, " ")}</span>
                    <span className="ml-2 text-[10px] text-[#8b949e] capitalize">
                      via {a.capture_method.replace(/_/g, " ")}
                    </span>
                  </div>
                  <span className="text-[10px] text-[#8b949e]">
                    {a.created_at ? new Date(a.created_at).toLocaleDateString() : ""}
                  </span>
                </div>
                {a.ai_summary && (
                  <p className="text-xs text-[#8b949e] mb-2 leading-relaxed">{a.ai_summary}</p>
                )}
                {a.score_leadership != null && (
                  <div className="flex gap-4 text-[10px]">
                    {[
                      { l: "Leadership", v: a.score_leadership },
                      { l: "Decision", v: a.score_decision_quality },
                      { l: "Stress", v: a.score_stress_response },
                      { l: "Tactical", v: a.score_tactical },
                      { l: "Comms", v: a.score_communication },
                    ].filter(x => x.v != null).map(x => (
                      <span key={x.l} className="text-[#8b949e]">
                        {x.l}: <span className="text-white">{x.v!.toFixed(1)}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
