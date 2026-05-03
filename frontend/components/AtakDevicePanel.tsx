"use client";

import { useCallback, useEffect, useState } from "react";
import { Link2, Loader2, MapPin, RefreshCw, Unlink } from "lucide-react";
import { api } from "@/lib/api";
import type { Soldier } from "@/types";

const LS_ID   = "c2d2_linked_soldier_id";
const LS_NAME = "c2d2_linked_soldier_name";

export interface GpsCoords {
  lat: number;
  lon: number;
  accuracy: number; // metres
}

interface Props {
  onLink: (soldierId: string, soldierName: string) => void;
  onGps:  (coords: GpsCoords | null) => void;
}

function fmt(g: GpsCoords): string {
  const lat = `${Math.abs(g.lat).toFixed(5)}°${g.lat >= 0 ? "N" : "S"}`;
  const lon = `${Math.abs(g.lon).toFixed(5)}°${g.lon >= 0 ? "E" : "W"}`;
  return `${lat}  ${lon}`;
}

export function AtakDevicePanel({ onLink, onGps }: Props) {
  const [gps,       setGps]       = useState<GpsCoords | null>(null);
  const [gpsState,  setGpsState]  = useState<"idle" | "loading" | "ok" | "denied">("idle");
  const [linked,    setLinked]    = useState<{ id: string; name: string } | null>(null);
  const [showForm,  setShowForm]  = useState(false);
  const [soldiers,  setSoldiers]  = useState<Soldier[]>([]);
  const [pickId,    setPickId]    = useState("");

  // Restore linked soldier from localStorage
  useEffect(() => {
    const id   = localStorage.getItem(LS_ID);
    const name = localStorage.getItem(LS_NAME);
    if (id && name) {
      setLinked({ id, name });
      onLink(id, name);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const requestGps = useCallback(() => {
    if (!("geolocation" in navigator)) { setGpsState("denied"); return; }
    setGpsState("loading");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const c: GpsCoords = {
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: Math.round(pos.coords.accuracy),
        };
        setGps(c);
        setGpsState("ok");
        onGps(c);
      },
      () => { setGpsState("denied"); onGps(null); },
      { enableHighAccuracy: true, timeout: 12000 },
    );
  }, [onGps]);

  useEffect(() => { requestGps(); }, [requestGps]);

  // Load soldier list when link form opens
  useEffect(() => {
    if (!showForm) return;
    api.get<Soldier[]>("/api/v1/soldiers").then(setSoldiers).catch(() => {});
  }, [showForm]);

  function confirmLink() {
    const s = soldiers.find(x => String(x.id) === pickId);
    if (!s) return;
    const name = `${s.rank} ${s.name}`;
    localStorage.setItem(LS_ID,   pickId);
    localStorage.setItem(LS_NAME, name);
    setLinked({ id: pickId, name });
    onLink(pickId, name);
    setShowForm(false);
    setPickId("");
  }

  function unlink() {
    localStorage.removeItem(LS_ID);
    localStorage.removeItem(LS_NAME);
    setLinked(null);
    onLink("", "");
  }

  return (
    <div className="bg-[#0d1117] border border-[#f59e0b]/40 rounded-lg p-3 space-y-2.5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-bold text-[#f59e0b] uppercase tracking-widest">ATAK Context</span>
        {gpsState === "loading" && <Loader2 size={10} className="text-[#8b949e] animate-spin" />}
        <span className="ml-auto text-[9px] text-[#6e7681] uppercase tracking-wider">Field Device</span>
      </div>

      {/* GPS row */}
      <div className="flex items-center gap-2 min-w-0">
        <MapPin size={13} className={gpsState === "ok" ? "text-[#3fb950] flex-shrink-0" : "text-[#4a5568] flex-shrink-0"} />
        <span className="text-[11px] font-mono truncate">
          {gpsState === "ok" && gps   ? <span className="text-[#e6edf3]">{fmt(gps)}</span>
          : gpsState === "loading"    ? <span className="text-[#8b949e]">Acquiring GPS…</span>
          : gpsState === "denied"     ? <span className="text-[#6e7681]">GPS unavailable</span>
          :                             null}
        </span>
        {gpsState !== "loading" && (
          <button
            type="button"
            onClick={requestGps}
            title="Refresh GPS"
            className="ml-auto flex-shrink-0 text-[#6e7681] hover:text-[#8b949e] transition-colors"
          >
            <RefreshCw size={11} />
          </button>
        )}
        {gpsState === "ok" && gps && (
          <span className="flex-shrink-0 text-[9px] text-[#6e7681]">±{gps.accuracy}m</span>
        )}
      </div>

      {/* Device link row */}
      <div className="flex items-center gap-2 min-w-0">
        <Link2 size={13} className={linked ? "text-[#3fb950] flex-shrink-0" : "text-[#4a5568] flex-shrink-0"} />
        {linked ? (
          <>
            <span className="text-[11px] text-white truncate">{linked.name}</span>
            <span className="ml-1 text-[9px] text-[#3fb950] flex-shrink-0 bg-[#3fb950]/10 px-1.5 py-0.5 rounded-full">linked</span>
            <button
              type="button"
              onClick={unlink}
              title="Unlink device"
              className="ml-auto flex-shrink-0 text-[#6e7681] hover:text-[#f85149] transition-colors"
            >
              <Unlink size={11} />
            </button>
          </>
        ) : (
          <>
            <span className="text-[11px] text-[#6e7681]">No soldier linked</span>
            <button
              type="button"
              onClick={() => setShowForm(v => !v)}
              className="ml-auto flex-shrink-0 text-[10px] font-semibold text-[#f59e0b] hover:underline transition-colors"
            >
              Link device
            </button>
          </>
        )}
      </div>

      {/* Link form */}
      {showForm && (
        <div className="flex gap-2 pt-1 border-t border-[#21262d]">
          <select
            value={pickId}
            onChange={e => setPickId(e.target.value)}
            className="flex-1 min-w-0 px-2 py-1.5 bg-[#161b22] border border-[#30363d] rounded text-xs text-white focus:outline-none focus:border-[#f59e0b]"
          >
            <option value="">Select soldier…</option>
            {soldiers.map(s => (
              <option key={s.id} value={String(s.id)}>{s.rank} {s.name}</option>
            ))}
          </select>
          <button
            type="button"
            onClick={confirmLink}
            disabled={!pickId}
            className="px-3 py-1.5 bg-[#f59e0b] text-black text-xs font-bold rounded disabled:opacity-40 flex-shrink-0"
          >
            Save
          </button>
        </div>
      )}
    </div>
  );
}
