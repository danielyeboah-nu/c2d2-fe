"use client";

import { useEffect, useState } from "react";
import { getQueueCount, drainQueue, subscribeQueueChange } from "@/lib/offlineQueue";

type SyncState = "idle" | "syncing" | "synced";

export function OfflineIndicator() {
  const [online, setOnline] = useState(true);
  const [queueCount, setQueueCount] = useState(0);
  const [syncState, setSyncState] = useState<SyncState>("idle");

  useEffect(() => {
    setOnline(navigator.onLine);
    getQueueCount().then(setQueueCount);

    const unsubQueue = subscribeQueueChange(setQueueCount);

    async function handleOnline() {
      setOnline(true);
      const count = await getQueueCount();
      if (count > 0) {
        setSyncState("syncing");
        await drainQueue();
        const remaining = await getQueueCount();
        setSyncState(remaining === 0 ? "synced" : "idle");
        if (remaining === 0) setTimeout(() => setSyncState("idle"), 3000);
      }
    }

    function handleOffline() {
      setOnline(false);
      setSyncState("idle");
    }

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      unsubQueue();
    };
  }, []);

  if (online && syncState === "idle" && queueCount === 0) return null;

  if (syncState === "synced") {
    return (
      <div className="fixed bottom-4 right-4 z-50 flex items-center gap-2 rounded-lg bg-green-900/90 px-4 py-2 text-sm font-medium text-green-100 shadow-lg backdrop-blur border border-green-700">
        <span className="h-2 w-2 rounded-full bg-green-400" />
        All data synced
      </div>
    );
  }

  if (syncState === "syncing") {
    return (
      <div className="fixed bottom-4 right-4 z-50 flex items-center gap-2 rounded-lg bg-blue-900/90 px-4 py-2 text-sm font-medium text-blue-100 shadow-lg backdrop-blur border border-blue-700">
        <span className="h-2 w-2 animate-pulse rounded-full bg-blue-400" />
        Syncing {queueCount} item{queueCount !== 1 ? "s" : ""}…
      </div>
    );
  }

  if (!online) {
    return (
      <div className="fixed bottom-4 right-4 z-50 flex items-center gap-2 rounded-lg bg-zinc-900/90 px-4 py-2 text-sm font-medium text-zinc-100 shadow-lg backdrop-blur border border-zinc-700">
        <span className="h-2 w-2 rounded-full bg-red-500" />
        Offline
        {queueCount > 0 && (
          <span className="rounded bg-zinc-700 px-1.5 py-0.5 text-xs text-zinc-300">
            {queueCount} pending
          </span>
        )}
      </div>
    );
  }

  // Online but still has queued items (transitional state during drain)
  return (
    <div className="fixed bottom-4 right-4 z-50 flex items-center gap-2 rounded-lg bg-amber-900/90 px-4 py-2 text-sm font-medium text-amber-100 shadow-lg backdrop-blur border border-amber-700">
      <span className="h-2 w-2 animate-pulse rounded-full bg-amber-400" />
      {queueCount} item{queueCount !== 1 ? "s" : ""} pending sync
    </div>
  );
}
