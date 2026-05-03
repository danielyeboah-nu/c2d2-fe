"use client";

import {
  createContext, useContext, useEffect, useRef, useState, useCallback,
} from "react";
import { api } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SimStatus = "pending" | "running" | "completed" | "failed";

export interface SimJob {
  jobId: number;
  sessionId: number;
  sessionName: string;
  status: SimStatus;
  simRound?: number;
  result?: Record<string, unknown>;
  error?: string;
}

interface SimJobResponse {
  job_id: number;
  session_id: number;
  sim_round: number;
  status: string;
  result?: Record<string, unknown>;
  error?: string;
}

interface SimContextValue {
  startTracking: (jobId: number, sessionId: number, sessionName: string) => void;
  getSessionJob: (sessionId: number) => SimJob | undefined;
  clearSessionJob: (sessionId: number) => void;
}

// ---------------------------------------------------------------------------
// Storage helpers
// ---------------------------------------------------------------------------

const STORAGE_KEY = "c2d2_sim_jobs";

function loadFromStorage(): Map<number, SimJob> {
  if (typeof window === "undefined") return new Map();
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const arr: SimJob[] = JSON.parse(stored);
      // Only restore jobs that are still in-flight
      const active = arr.filter(j => j.status === "pending" || j.status === "running");
      return new Map(active.map(j => [j.jobId, j]));
    }
  } catch {}
  return new Map();
}

function persistActive(jobs: Map<number, SimJob>) {
  const active = Array.from(jobs.values()).filter(
    j => j.status === "pending" || j.status === "running",
  );
  if (active.length === 0) {
    localStorage.removeItem(STORAGE_KEY);
  } else {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(active));
  }
}

// ---------------------------------------------------------------------------
// Notification helper
// ---------------------------------------------------------------------------

function showSimNotification(sessionName: string) {
  if (typeof window === "undefined" || !("Notification" in window)) return;

  const fire = () => {
    if (!document.hidden) return; // user is looking at the page — no need to notify
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.ready
        .then(reg =>
          reg.showNotification("ATHENA — Simulation Complete", {
            body: `Analysis ready for: ${sessionName}`,
            icon: "/icon.svg",
            tag: "sim-complete",
            data: { path: "/battlespace" },
          }),
        )
        .catch(() => {});
    }
  };

  if (Notification.permission === "granted") {
    fire();
  } else if (Notification.permission !== "denied") {
    Notification.requestPermission().then(perm => {
      if (perm === "granted") fire();
    });
  }
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const SimContext = createContext<SimContextValue>({
  startTracking: () => {},
  getSessionJob: () => undefined,
  clearSessionJob: () => {},
});

export function SimulationProvider({ children }: { children: React.ReactNode }) {
  const [jobs, setJobs] = useState<Map<number, SimJob>>(loadFromStorage);
  const jobsRef = useRef<Map<number, SimJob>>(jobs);

  // Keep ref in sync so the interval always reads the latest state
  useEffect(() => {
    jobsRef.current = jobs;
    persistActive(jobs);
  }, [jobs]);

  // Single long-lived polling interval — reads from ref, not closure
  useEffect(() => {
    const interval = setInterval(async () => {
      const active = Array.from(jobsRef.current.values()).filter(
        j => j.status === "pending" || j.status === "running",
      );
      if (active.length === 0) return;

      for (const job of active) {
        try {
          const data = await api.get<SimJobResponse>(
            `/api/v1/battlespace/jobs/${job.jobId}`,
          );
          const newStatus = data.status as SimStatus;
          if (newStatus !== job.status) {
            setJobs(prev => {
              const next = new Map(prev);
              next.set(job.jobId, {
                ...job,
                status: newStatus,
                simRound: data.sim_round,
                result: data.result ?? undefined,
                error: data.error ?? undefined,
              });
              return next;
            });
            if (newStatus === "completed") {
              showSimNotification(job.sessionName);
            }
          }
        } catch {
          // Network errors during poll are silently ignored
        }
      }
    }, 3000);

    return () => clearInterval(interval);
  }, []); // intentionally empty — interval is permanent, reads via ref

  const startTracking = useCallback(
    (jobId: number, sessionId: number, sessionName: string) => {
      setJobs(prev => {
        const next = new Map(prev);
        next.set(jobId, { jobId, sessionId, sessionName, status: "pending" });
        return next;
      });
    },
    [],
  );

  const getSessionJob = useCallback((sessionId: number) => {
    return Array.from(jobsRef.current.values()).find(j => j.sessionId === sessionId);
  }, []);

  const clearSessionJob = useCallback((sessionId: number) => {
    setJobs(prev => {
      const next = new Map(prev);
      for (const [jobId, job] of next) {
        if (job.sessionId === sessionId) next.delete(jobId);
      }
      return next;
    });
  }, []);

  return (
    <SimContext.Provider value={{ startTracking, getSessionJob, clearSessionJob }}>
      {children}
    </SimContext.Provider>
  );
}

export function useSimulation() {
  return useContext(SimContext);
}
