"use client";

import { useEffect, useRef, useState } from "react";
import { Play, Terminal, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useMounted } from "@/lib/use-client-store";

type Source = { label: string; path: string };

/** In-browser JupyterLite plus a server sandbox, both pre-filled from the same notebook source. */
export function NotebookWorkbench({ source, recent }: { source: Source; recent: Source[] }) {
  const [tab, setTab] = useState<"browser" | "sandbox">("browser");
  const [code, setCode] = useState(`import json\nprint("hello from the sandbox")\nprint(json.dumps({"tokens": 42, "cost_usd": 0.0003}))`);
  const [result, setResult] = useState<{ stdout: string; stderr: string; exit_code: number; ms: number; backend: string } | null>(null);
  const [running, setRunning] = useState(false);
  const mounted = useMounted();
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [liteState, setLiteState] = useState<"loading" | "ready" | "failed">("loading");
  const fileName = source.path.split("/").pop() ?? "notebook.ipynb";
  const liteSrc = "/jupyterlite/lab/index.html";

  // The runtime exposes its app on the iframe window (same origin). We fetch the generated notebook with the
  // user's cookies, save it through the runtime's contents API, and open it: a real per-user prefill.
  useEffect(() => {
    if (!mounted) return;
    let cancelled = false;
    let attempts = 0;
    const timer = setInterval(async () => {
      type LiteApp = { serviceManager: { contents: { save: (path: string, model: object) => Promise<unknown> } }; commands: { execute: (id: string, args: object) => Promise<unknown> } };
      const app = (frameRef.current?.contentWindow as (Window & { jupyterapp?: LiteApp }) | null)?.jupyterapp;
      attempts += 1;
      if (!app) { if (attempts > 180) { clearInterval(timer); setLiteState("failed"); } return; }  // the runtime can take a while on a busy machine
      clearInterval(timer);
      try {
        const res = await fetch(`/api/pg${source.path}`);
        const nb = await res.json();
        await app.serviceManager.contents.save(fileName, { type: "notebook", format: "json", content: nb });
        await app.commands.execute("docmanager:open", { path: fileName });
        if (!cancelled) setLiteState("ready");
      } catch {
        if (!cancelled) setLiteState("failed");
      }
    }, 500);
    return () => { cancelled = true; clearInterval(timer); };
  }, [mounted, source.path, fileName]);

  const run = async () => {
    setRunning(true);
    const res = await fetch("/api/pg/v1/sandbox/execute", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ code }) });
    setResult(res.ok ? await res.json() : { stdout: "", stderr: `Request failed (${res.status})`, exit_code: 1, ms: 0, backend: "?" });
    setRunning(false);
  };

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Build</p>
          <h1 className="text-2xl font-semibold tracking-tight">Notebooks</h1>
          <p className="mt-1 text-sm text-muted-foreground">Open any run, conversation or blueprint as a notebook. In-browser Python costs nothing to host; the server sandbox runs real packages.</p>
        </div>
        <div role="tablist" aria-label="Notebook mode" className="flex rounded-lg border bg-card p-0.5 text-xs">
          <button type="button" role="tab" aria-selected={tab === "browser"} onClick={() => setTab("browser")} className={cn("flex h-7 items-center gap-1 rounded-md px-2.5", tab === "browser" && "bg-secondary text-secondary-foreground")}><Globe className="size-3.5" /> In browser</button>
          <button type="button" role="tab" aria-selected={tab === "sandbox"} onClick={() => setTab("sandbox")} className={cn("flex h-7 items-center gap-1 rounded-md px-2.5", tab === "sandbox" && "bg-secondary text-secondary-foreground")}><Terminal className="size-3.5" /> Server sandbox</button>
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[240px_1fr]">
        <aside className="rounded-2xl border bg-card p-3" aria-label="Notebook sources">
          <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Open as notebook</p>
          <ul className="mt-2 space-y-1 text-xs">
            {recent.map((r) => (
              <li key={r.path}>
                <a href={`/build/notebooks?source=${encodeURIComponent(r.path)}`} className={cn("block truncate rounded-lg px-2 py-1.5 hover:bg-muted", r.path === source.path && "bg-secondary text-secondary-foreground")} title={r.label}>{r.label}</a>
              </li>
            ))}
          </ul>
        </aside>

        {tab === "browser" ? (
          <section className="overflow-hidden rounded-2xl border bg-card" aria-label="In-browser notebook">
            <div className="flex items-center justify-between border-b px-3 py-2 text-xs text-muted-foreground">
              <span>JupyterLite · Pyodide kernel · {source.label} · <span data-testid="lite-state" className={liteState === "ready" ? "text-brand-emerald" : liteState === "failed" ? "text-brand-rose" : ""}>{liteState === "ready" ? `${fileName} opened` : liteState === "failed" ? "could not open the notebook" : "loading runtime…"}</span></span>
              <a href={liteSrc} target="_blank" rel="noreferrer" className="text-brand-violet-soft hover:underline">Open full screen</a>
            </div>
            {mounted ? <iframe ref={frameRef} title="JupyterLite notebook" src={liteSrc} className="h-[70vh] w-full bg-white" data-testid="jupyterlite-frame" /> : <div className="h-[70vh] w-full animate-pulse bg-muted" aria-hidden />}
          </section>
        ) : (
          <section className="rounded-2xl border bg-card p-4" aria-label="Server sandbox">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Python in an isolated process with your playground identity. Production uses Azure Container Apps dynamic sessions at $0.03 per session-hour.</span>
              <Button size="sm" className="glow-violet" onClick={run} disabled={running} aria-label="Run in sandbox"><Play className="size-3.5" /> {running ? "Running…" : "Run"}</Button>
            </div>
            <textarea value={code} onChange={(e) => setCode(e.target.value)} rows={12} aria-label="Sandbox code" className="mt-3 w-full rounded-xl border bg-[#0d0d18] p-3 font-mono text-[12.5px] leading-6 text-slate-100 outline-none" />
            {result && (
              <div className="mt-3 rounded-xl border bg-muted/40 p-3 font-mono text-[12px]" data-testid="sandbox-output">
                <p className="mb-1 text-[10.5px] text-muted-foreground">exit {result.exit_code} · {result.ms} ms · backend {result.backend}</p>
                {result.stdout && <pre className="whitespace-pre-wrap">{result.stdout}</pre>}
                {result.stderr && <pre className="whitespace-pre-wrap text-brand-rose">{result.stderr}</pre>}
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
