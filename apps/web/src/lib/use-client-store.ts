"use client";

import { useSyncExternalStore } from "react";

const noop = () => () => {};

/** True after hydration, false during server render. Avoids setState-in-effect for mount gating. */
export function useMounted(): boolean {
  return useSyncExternalStore(noop, () => true, () => false);
}

const listeners = new Set<() => void>();
function emit() { listeners.forEach((l) => l()); }

/** Boolean persisted in localStorage, hydration-safe (server snapshot is the fallback). */
export function useStoredBoolean(key: string, fallback = false): [boolean, (next: boolean) => void] {
  const subscribe = (cb: () => void) => {
    listeners.add(cb);
    const onStorage = (e: StorageEvent) => { if (e.key === key) cb(); };
    window.addEventListener("storage", onStorage);
    return () => { listeners.delete(cb); window.removeEventListener("storage", onStorage); };
  };
  const read = () => {
    try { const v = window.localStorage.getItem(key); return v === null ? fallback : v === "1"; } catch { return fallback; }
  };
  const value = useSyncExternalStore(subscribe, read, () => fallback);
  const set = (next: boolean) => {
    try { window.localStorage.setItem(key, next ? "1" : "0"); } catch { /* storage unavailable */ }
    emit();
  };
  return [value, set];
}

/** Time-of-day greeting, computed on the client only; the server renders "Welcome". */
export function useGreetingWord(): string {
  return useSyncExternalStore(
    noop,
    () => {
      const h = new Date().getHours();
      return h < 5 ? "Good night" : h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
    },
    () => "Welcome",
  );
}
