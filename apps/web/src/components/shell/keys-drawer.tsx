"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, ExternalLink, KeyRound, Loader2, ShieldCheck, Trash2 } from "lucide-react";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import type { ProviderKeyStatus } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

type KeysResponse = { providers: ProviderKeyStatus[]; scope: "all" | "platform-only"; scope_note: string };

export const OPEN_KEYS_EVENT = "playground:open-keys";
export const KEYS_CHANGED_EVENT = "playground:keys-changed";

/** Open the Keys drawer from anywhere (a "Needs key" badge, a blocked chat), optionally focused on one provider. */
export function openKeysDrawer(provider?: string) {
  window.dispatchEvent(new CustomEvent(OPEN_KEYS_EVENT, { detail: { provider } }));
}

export const providerSlug = (provider: string) => provider.toLowerCase().replace(/[^a-z0-9]+/g, "-");

export function KeysDrawer() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [focus, setFocus] = useState<string | null>(null);
  const [data, setData] = useState<KeysResponse | null>(null);

  const load = useCallback(
    () => fetch("/api/pg/v1/keys").then((r) => (r.ok ? r.json() : null)).then((j: KeysResponse | null) => { if (j) setData(j); }).catch(() => {}),
    [],
  );
  useEffect(() => {
    void load();
    const onOpen = (e: Event) => { setFocus((e as CustomEvent<{ provider?: string }>).detail?.provider ?? null); setOpen(true); };
    window.addEventListener(OPEN_KEYS_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_KEYS_EVENT, onOpen);
  }, [load]);
  useEffect(() => { if (open) void load(); }, [open, load]);

  const changed = () => { void load(); window.dispatchEvent(new Event(KEYS_CHANGED_EVENT)); router.refresh(); };
  const usable = data?.providers.filter((p) => p.usable).length ?? 0;
  const total = data?.providers.length ?? 0;
  const personal = data?.providers.filter((p) => p.personal).length ?? 0;
  const ordered = data ? [...data.providers].sort((a, b) => (a.provider === focus ? -1 : b.provider === focus ? 1 : 0)) : [];

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <button
        type="button"
        onClick={() => { setFocus(null); setOpen(true); }}
        data-testid="keys-chip"
        aria-label="Provider keys"
        title="Provider keys: yours and the platform's"
        className="hidden h-8 items-center gap-1.5 rounded-lg border bg-card px-2.5 text-xs text-muted-foreground hover:border-brand-violet/40 hover:text-foreground md:flex"
      >
        <KeyRound className="size-3.5" />
        <span>Keys</span>
        {data && <span className={cn("rounded-full px-1.5 text-[10px] font-medium", usable ? "bg-brand-emerald/15 text-brand-emerald" : "bg-brand-amber/15 text-brand-amber")}>{usable}/{total}</span>}
      </button>
      <SheetContent side="right" className="w-full overflow-y-auto p-0 sm:max-w-md" data-testid="keys-drawer">
        <SheetHeader className="p-5 pb-2">
          <SheetTitle className="flex items-center gap-2"><KeyRound className="size-4 text-brand-violet-soft" /> Provider keys</SheetTitle>
          <SheetDescription>
            Bring your own keys, exactly like the OpenAI or Claude playgrounds. Your key is used first; when the platform holds a key for a provider it serves you as well.
            Keys are encrypted at rest and only the last four characters are ever shown.
          </SheetDescription>
        </SheetHeader>
        {data && (
          <div className="mx-5 mb-3 flex items-center gap-2 rounded-lg border bg-muted/40 px-3 py-2 text-[11px] text-muted-foreground">
            <ShieldCheck className="size-3.5 shrink-0 text-brand-emerald" />
            <span>{data.scope_note}. {personal ? `${personal} personal key${personal === 1 ? "" : "s"} saved.` : "No personal keys saved yet."}</span>
          </div>
        )}
        {!data && <p className="px-5 text-xs text-muted-foreground">Loading providers…</p>}
        <ul className="divide-y border-t" aria-label="Providers">
          {ordered.map((p) => <ProviderRow key={p.provider} p={p} focused={p.provider === focus} onChanged={changed} />)}
        </ul>
        <p className="px-5 py-4 text-[11px] text-muted-foreground">
          The platform&apos;s own keys run its agents, evaluations and canaries and are never shown. An admin decides in Settings whether they also serve people.
        </p>
      </SheetContent>
    </Sheet>
  );
}

function ProviderRow({ p, focused, onChanged }: { p: ProviderKeyStatus; focused: boolean; onChanged: () => void }) {
  const slug = providerSlug(p.provider);
  const [editing, setEditing] = useState(focused && !p.personal);
  const [value, setValue] = useState("");
  const [base, setBase] = useState("");
  const [busy, setBusy] = useState<"save" | "test" | "remove" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ ok: boolean; text: string } | null>(null);

  const save = async () => {
    setBusy("save"); setError(null);
    const res = await fetch(`/api/pg/v1/keys/${encodeURIComponent(p.provider)}`, {
      method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify({ key: value, api_base: base || null }),
    });
    setBusy(null);
    if (!res.ok) { setError((await res.json().catch(() => ({}))).detail ?? "Could not save the key"); return; }
    setValue(""); setBase(""); setEditing(false); setTestResult(null); onChanged();
  };
  const test = async () => {
    setBusy("test"); setTestResult(null);
    const j = await fetch(`/api/pg/v1/keys/${encodeURIComponent(p.provider)}/test`, { method: "POST" }).then((r) => r.json()).catch(() => ({ ok: false, error: "Request failed" }));
    setBusy(null);
    setTestResult(j.ok ? { ok: true, text: `Works · ${j.model} replied via ${j.source === "personal" ? "your key" : j.source === "platform" ? "the platform key" : "the offline provider"}` } : { ok: false, text: j.error ?? "Failed" });
  };
  const remove = async () => {
    setBusy("remove");
    await fetch(`/api/pg/v1/keys/${encodeURIComponent(p.provider)}`, { method: "DELETE" });
    setBusy(null); setTestResult(null); onChanged();
  };

  const status = p.personal
    ? { label: `Your key ••••${p.personal.last4}`, cls: "bg-brand-violet/15 text-brand-violet-soft" }
    : p.source === "platform"
      ? { label: "Platform key", cls: "bg-brand-emerald/15 text-brand-emerald" }
      : p.source === "fake"
        ? { label: "Offline provider", cls: "bg-brand-cyan/15 text-brand-cyan" }
        : { label: "Not set", cls: "bg-muted text-muted-foreground" };

  return (
    <li className={cn("px-5 py-3", focused && "bg-brand-violet/5")} data-testid={`key-row-${slug}`}>
      <div className="flex items-center gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">{p.provider} <span className="text-[11px] font-normal text-muted-foreground">· {p.models} model{p.models === 1 ? "" : "s"}</span></p>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px]">
            <a href={p.key_page} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">Get a key <ExternalLink className="size-3" /></a>
            <a href={p.docs} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground">Docs <ExternalLink className="size-3" /></a>
            <a href={p.pricing} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground">Pricing <ExternalLink className="size-3" /></a>
          </div>
        </div>
        <span className={cn("shrink-0 rounded-full px-2 py-0.5 text-[10.5px] font-medium", status.cls)} data-testid={`key-status-${slug}`}>{status.label}</span>
      </div>

      {editing ? (
        <form className="mt-2 space-y-2" onSubmit={(e) => { e.preventDefault(); void save(); }}>
          <label className="block text-[11px] text-muted-foreground">
            <span className="sr-only">{p.provider} API key</span>
            <input
              type="password" autoComplete="off" spellCheck={false} value={value} onChange={(e) => setValue(e.target.value)}
              placeholder={p.prefix ? `${p.prefix}…` : "API key"} aria-label={`${p.provider} API key`}
              className="h-8 w-full rounded-md border bg-background px-2 font-mono text-xs"
            />
          </label>
          {p.needs_base && (
            <input
              value={base} onChange={(e) => setBase(e.target.value)} placeholder="https://<resource>.openai.azure.com" aria-label={`${p.provider} endpoint`}
              className="h-8 w-full rounded-md border bg-background px-2 font-mono text-xs"
            />
          )}
          {error && <p className="text-[11px] text-brand-rose">{error}</p>}
          <div className="flex gap-2">
            <button type="submit" disabled={busy === "save" || value.trim().length < 8} className="inline-flex h-7 items-center gap-1 rounded-md bg-primary px-2.5 text-xs font-medium text-primary-foreground disabled:opacity-50">
              {busy === "save" ? <Loader2 className="size-3 animate-spin" /> : <Check className="size-3" />} Save key
            </button>
            <button type="button" onClick={() => { setEditing(false); setError(null); }} className="h-7 rounded-md border px-2.5 text-xs">Cancel</button>
          </div>
        </form>
      ) : (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <button type="button" onClick={() => setEditing(true)} className="h-7 rounded-md border px-2.5 text-xs hover:border-brand-violet/40">{p.personal ? "Replace key" : "Add key"}</button>
          {p.usable && (
            <button type="button" onClick={() => void test()} disabled={busy === "test"} className="inline-flex h-7 items-center gap-1 rounded-md border px-2.5 text-xs hover:border-brand-violet/40 disabled:opacity-50">
              {busy === "test" && <Loader2 className="size-3 animate-spin" />} Test key
            </button>
          )}
          {p.personal && (
            <button type="button" onClick={() => void remove()} disabled={busy === "remove"} className="inline-flex h-7 items-center gap-1 rounded-md border px-2.5 text-xs text-brand-rose hover:border-brand-rose/50 disabled:opacity-50" aria-label="Remove key">
              <Trash2 className="size-3" /> Remove key
            </button>
          )}
        </div>
      )}
      {testResult && <p className={cn("mt-1.5 text-[11px]", testResult.ok ? "text-brand-emerald" : "text-brand-rose")} data-testid="key-test-result">{testResult.text}</p>}
    </li>
  );
}
