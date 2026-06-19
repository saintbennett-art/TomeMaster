// [FILES-ONLY PREFERENCES]: global app/UI preferences live in the encrypted vault
// (settings.enc → preferences), NOT in browser localStorage. This module loads them
// once at startup into an in-memory cache so synchronous React initializers (theme,
// dialog positions) can read them without a flash, and writes through to the backend
// on every change. Dependency-free beyond the api client → reusable in any project.

import { getPreferences, updatePreferences } from "./apiClient";

type Prefs = Record<string, unknown>;

let cache: Prefs = {};
let loaded = false;
let loadingPromise: Promise<void> | null = null;

/** Load the vault preferences into the in-memory cache exactly once. Call early
 *  (app startup). Idempotent — concurrent callers share one network round-trip. */
export async function loadPreferences(): Promise<void> {
    if (loaded) return;
    if (!loadingPromise) {
        loadingPromise = getPreferences().then((p) => {
            cache = p || {};
            loaded = true;
        }).catch(() => { loaded = true; });
    }
    return loadingPromise;
}

export function prefsReady(): boolean {
    return loaded;
}

/** Synchronous read from the cache (use in useState initializers). Returns
 *  `fallback` when the key is absent or prefs haven't loaded yet. */
export function getPref<T>(key: string, fallback: T): T {
    if (key in cache && cache[key] !== undefined && cache[key] !== null) {
        return cache[key] as T;
    }
    return fallback;
}

/** Write-through: update the cache immediately (so subsequent sync reads are
 *  correct) and persist to the vault. Fire-and-forget on the network side. */
export function setPref(key: string, value: unknown): void {
    cache[key] = value;
    updatePreferences({ [key]: value });
}

// ─── UI layout (draggable panel positions + lock state) ────────────────────────
// Stored as one map under the `ui_layout` preference: { <id>: { pos?, locked? } }.

export interface PanelLayout { pos?: { x: number; y: number }; locked?: boolean }

export function getLayout(id: string): PanelLayout {
    const all = getPref<Record<string, PanelLayout>>('ui_layout', {});
    return all[id] || {};
}

export function setLayout(id: string, patch: PanelLayout): void {
    const all = { ...getPref<Record<string, PanelLayout>>('ui_layout', {}) };
    all[id] = { ...(all[id] || {}), ...patch };
    setPref('ui_layout', all);
}
