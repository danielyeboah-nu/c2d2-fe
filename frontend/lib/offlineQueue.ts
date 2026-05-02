import { getToken } from "./auth";

const DB_NAME = "c2d2_offline";
const DB_VERSION = 1;
const STORE = "queue";
const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const MAX_RETRIES = 5;

export interface QueueEntry {
  id?: number;
  timestamp: number;
  method: string;
  path: string;
  jsonBody: string | null;
  formFields: { key: string; value: string }[] | null;
  formFiles: { key: string; blob: Blob; filename: string; mimeType: string }[] | null;
  isFormData: boolean;
  retries: number;
}

type ChangeListener = (count: number) => void;
const changeListeners = new Set<ChangeListener>();

export function subscribeQueueChange(fn: ChangeListener) {
  changeListeners.add(fn);
  return () => changeListeners.delete(fn);
}

async function notifyChange() {
  if (typeof indexedDB === "undefined") return;
  const count = await getQueueCount();
  changeListeners.forEach((fn) => fn(count));
}

let _db: IDBDatabase | null = null;

function openDB(): Promise<IDBDatabase> {
  if (_db) return Promise.resolve(_db);
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (e) => {
      const database = (e.target as IDBOpenDBRequest).result;
      if (!database.objectStoreNames.contains(STORE)) {
        database.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
      }
    };
    req.onsuccess = (e) => {
      _db = (e.target as IDBOpenDBRequest).result;
      resolve(_db);
    };
    req.onerror = (e) => reject((e.target as IDBOpenDBRequest).error);
  });
}

export async function enqueue(entry: Omit<QueueEntry, "id">): Promise<void> {
  if (typeof indexedDB === "undefined") return;
  const db = await openDB();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    const req = tx.objectStore(STORE).add(entry);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
  await notifyChange();
}

export async function getQueueCount(): Promise<number> {
  if (typeof indexedDB === "undefined") return 0;
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const req = tx.objectStore(STORE).count();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function getAllEntries(): Promise<QueueEntry[]> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const req = tx.objectStore(STORE).getAll();
    req.onsuccess = () => resolve(req.result as QueueEntry[]);
    req.onerror = () => reject(req.error);
  });
}

async function deleteEntry(id: number): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    const req = tx.objectStore(STORE).delete(id);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

async function updateEntry(entry: QueueEntry): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    const req = tx.objectStore(STORE).put(entry);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

async function replayEntry(entry: QueueEntry): Promise<boolean> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let body: BodyInit;
  if (entry.isFormData) {
    const form = new FormData();
    for (const { key, value } of entry.formFields ?? []) {
      form.append(key, value);
    }
    for (const { key, blob, filename, mimeType } of entry.formFiles ?? []) {
      form.append(key, new File([blob], filename, { type: mimeType }));
    }
    body = form;
  } else {
    headers["Content-Type"] = "application/json";
    body = entry.jsonBody ?? "{}";
  }

  const res = await fetch(`${BASE}${entry.path}`, {
    method: entry.method,
    headers,
    body,
  });

  return res.ok;
}

export interface DrainResult {
  synced: number;
  failed: number;
}

export async function drainQueue(): Promise<DrainResult> {
  if (typeof indexedDB === "undefined") return { synced: 0, failed: 0 };
  const entries = await getAllEntries();
  let synced = 0;
  let failed = 0;

  for (const entry of entries) {
    try {
      const ok = await replayEntry(entry);
      if (ok) {
        await deleteEntry(entry.id!);
        await notifyChange();
        synced++;
      } else {
        const retries = (entry.retries ?? 0) + 1;
        if (retries >= MAX_RETRIES) {
          await deleteEntry(entry.id!);
          await notifyChange();
          console.warn(`[C2D2] Dropped queued ${entry.method} ${entry.path} after ${MAX_RETRIES} retries`);
          failed++;
        } else {
          await updateEntry({ ...entry, retries });
          failed++;
        }
      }
    } catch {
      // Network error — leave in queue for next sync attempt
      failed++;
    }
  }

  return { synced, failed };
}
