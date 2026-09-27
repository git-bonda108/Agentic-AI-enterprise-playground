"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { BookOpen, Download, ExternalLink, Globe, Loader2, Package, Play, Rocket, Terminal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useMounted } from "@/lib/use-client-store";

type Source = { label: string; path: string };
export type GalleryItem = { slug: string; title: string; blurb: string; category: "Gen AI" | "Agentic AI"; level: "Starter" | "Intermediate" | "Advanced"; minutes: number; tags: string[]; path: string; kind: string; blueprint_id?: string };
export type ComputeOption = { id: string; name: string; cost: string; blurb: string; action: "open" | "run" | "link"; url?: string; download_first?: boolean; docs?: string };
type Cell = { cell_type: "markdown" | "code"; source: string | string[] };
type CellResult = { cell: number; stdout: string; error: string | null };
type ExecResult = { ok: boolean; cells: CellResult[]; stderr: string; exit_code: number; ms: number; backend: string };

const LEVEL_STYLE: Record<GalleryItem["level"], string> = { Starter: "bg-brand-emerald/15 text-brand-emerald", Intermediate: "bg-brand-cyan/15 text-brand-cyan", Advanced: "bg-brand-pink/15 text-brand-pink" };
const text = (c: Cell) => (Array.isArray(c.source) ? c.source.join("") : c.source);

/** Gallery of runnable notebooks, the in-browser runtime, and a sandbox that runs a whole notebook cell by cell. */
export function NotebookWorkbench({ source, recent, gallery, compute, showGallery, autorun }: { source: Source; recent: Source[]; gallery: GalleryItem[]; compute: ComputeOption[]; showGallery: boolean; autorun: boolean }) {
  const [tab, setTab] = useState<"browser" | "sandbox">(autorun ? "sandbox" : "browser");
  const [moreCompute, setMoreCompute] = useState(false);
  const fileName = source.path.split("/").pop() ?? "notebook.ipynb";

  // Editor activity feeds the adoption clock: one zero-cost row every three minutes while the tab is visible.
  useEffect(() => {
    if (showGallery) return;
    const beat = () => { if (document.visibilityState === "visible") void fetch("/api/pg/v1/notebooks/heartbeat", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ path: source.path, mode: tab }) }).catch(() => {}); };
    beat();
    const timer = setInterval(beat, 180_000);
    return () => clearInterval(timer);
  }, [showGallery, source.path, tab]);

  const download = async () => {
    const res = await fetch(`/api/pg${source.path}`);
    const blob = new Blob([await res.text()], { type: "application/x-ipynb+json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Build</p>
          <h1 className="text-2xl font-semibold tracking-tight">Notebooks</h1>
          <p className="mt-1 text-sm text-muted-foreground">Every blueprint runs end to end on mock data from the first cell. Start in the browser, run the whole notebook in the sandbox, or take it to GPU compute.</p>
        </div>
        {!showGallery && (
          <div className="flex flex-wrap items-center gap-2">
            <div role="tablist" aria-label="Compute" className="flex rounded-lg border bg-card p-0.5 text-xs">
              <button type="button" role="tab" aria-selected={tab === "browser"} onClick={() => setTab("browser")} className={cn("flex h-7 items-center gap-1 rounded-md px-2.5", tab === "browser" && "bg-secondary text-secondary-foreground")}><Globe className="size-3.5" /> In browser</button>
              <button type="button" role="tab" aria-selected={tab === "sandbox"} onClick={() => setTab("sandbox")} className={cn("flex h-7 items-center gap-1 rounded-md px-2.5", tab === "sandbox" && "bg-secondary text-secondary-foreground")}><Terminal className="size-3.5" /> Server sandbox</button>
              <button type="button" aria-expanded={moreCompute} onClick={() => setMoreCompute((v) => !v)} className={cn("flex h-7 items-center gap-1 rounded-md px-2.5", moreCompute && "bg-secondary text-secondary-foreground")}><Rocket className="size-3.5" /> More compute</button>
            </div>
            <Button size="sm" variant="outline" onClick={() => void download()} aria-label="Download notebook"><Download className="size-3.5" /> Download</Button>
          </div>
        )}
      </div>

      {showGallery ? (
        <Gallery items={gallery} />
      ) : (
        <>
          {moreCompute && <ComputePanel options={compute.filter((o) => o.action === "link")} onDownload={download} />}
          <div className="mt-5 grid gap-4 lg:grid-cols-[240px_1fr]">
            <aside className="rounded-2xl border bg-card p-3" aria-label="Notebook sources">
              <Link href="/build/notebooks" className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium hover:bg-muted"><BookOpen className="size-3.5 text-brand-violet-soft" /> Gallery</Link>
              <p className="mt-2 px-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Open as notebook</p>
              <ul className="mt-1 space-y-1 text-xs">
                {recent.map((r) => (
                  <li key={r.path}>
                    <a href={`/build/notebooks?source=${encodeURIComponent(r.path)}`} className={cn("block truncate rounded-lg px-2 py-1.5 hover:bg-muted", r.path === source.path && "bg-secondary text-secondary-foreground")} title={r.label}>{r.label}</a>
                  </li>
                ))}
              </ul>
            </aside>
            {tab === "browser" ? <BrowserRuntime source={source} fileName={fileName} /> : <SandboxRunner source={source} autorun={autorun} />}
          </div>
        </>
      )}
    </div>
  );
}

function Gallery({ items }: { items: GalleryItem[] }) {
  const [level, setLevel] = useState<"All" | GalleryItem["level"]>("All");
  const shown = items.filter((i) => level === "All" || i.level === level);
  const groups: GalleryItem["category"][] = ["Gen AI", "Agentic AI"];
  return (
    <div className="mt-5" data-testid="notebook-gallery">
      <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Level">
        {(["All", "Starter", "Intermediate", "Advanced"] as const).map((l) => (
          <button key={l} type="button" aria-pressed={level === l} onClick={() => setLevel(l)} className={cn("h-7 rounded-md border px-2.5 text-xs", level === l ? "border-brand-violet/60 bg-brand-violet/10" : "text-muted-foreground hover:text-foreground")}>{l}</button>
        ))}
        <span className="ml-auto text-[11px] text-muted-foreground">{shown.length} notebooks · each one runs on mock data with your key</span>
      </div>
      {groups.map((g) => {
        const rows = shown.filter((i) => i.category === g);
        if (!rows.length) return null;
        return (
          <section key={g} className="mt-5" aria-label={`${g} notebooks`}>
            <h2 className="text-sm font-semibold">{g} <span className="ml-1 text-xs font-normal text-muted-foreground">{g === "Gen AI" ? "single-model patterns: chat, retrieval, extraction, analysis" : "multi-step agents with tools, checkpoints and human review"}</span></h2>
            <div className="mt-2 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {rows.map((i) => (
                <article key={i.slug} className="flex flex-col rounded-2xl border bg-card p-4" data-testid={`gallery-${i.slug}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className={cn("rounded-md px-1.5 py-0.5 text-[10px] font-medium", LEVEL_STYLE[i.level])}>{i.level}</span>
                    <span className="text-[11px] text-muted-foreground">{i.minutes} min</span>
                  </div>
                  <h3 className="mt-2 text-sm font-semibold">{i.title}</h3>
                  <p className="mt-1 text-xs text-muted-foreground">{i.blurb}</p>
                  <div className="mt-2 flex flex-wrap gap-1">{i.tags.filter(Boolean).map((t) => <span key={t} className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">{t}</span>)}</div>
                  <div className="mt-auto flex items-center gap-2 pt-3">
                    <Link href={`/build/notebooks?source=${encodeURIComponent(i.path)}`} className="inline-flex h-8 items-center gap-1 rounded-lg bg-primary px-3 text-xs font-medium text-primary-foreground"><Globe className="size-3" /> Open</Link>
                    <Link href={`/build/notebooks?source=${encodeURIComponent(i.path)}&run=sandbox`} className="inline-flex h-8 items-center gap-1 rounded-lg border px-3 text-xs hover:border-brand-violet/40"><Play className="size-3" /> Run in sandbox</Link>
                  </div>
                </article>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function ComputePanel({ options, onDownload }: { options: ComputeOption[]; onDownload: () => Promise<void> }) {
  return (
    <div className="mt-4 grid gap-3 md:grid-cols-3" data-testid="compute-panel">
      {options.map((o) => (
        <article key={o.id} className="rounded-2xl border bg-card p-4">
          <div className="flex items-center justify-between"><h3 className="text-sm font-semibold">{o.name}</h3><span className="text-[11px] text-muted-foreground">{o.cost}</span></div>
          <p className="mt-1 text-xs text-muted-foreground">{o.blurb}</p>
          {o.download_first && <p className="mt-2 text-[11px] text-brand-amber">Download the notebook first, then upload it there. Deep links with the notebook preloaded work once the playground has a public address.</p>}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {o.download_first && <button type="button" onClick={() => void onDownload()} className="inline-flex h-7 items-center gap-1 rounded-md border px-2.5 text-xs"><Download className="size-3" /> Download</button>}
            <a href={o.url} target="_blank" rel="noreferrer" className="inline-flex h-7 items-center gap-1 rounded-md bg-primary px-2.5 text-xs font-medium text-primary-foreground">Open {o.name} <ExternalLink className="size-3" /></a>
            {o.docs && <a href={o.docs} target="_blank" rel="noreferrer" className="inline-flex h-7 items-center gap-1 px-1 text-xs text-muted-foreground hover:text-foreground">Docs <ExternalLink className="size-3" /></a>}
          </div>
        </article>
      ))}
    </div>
  );
}

type LiteWidget = { id: string };
type LiteApp = {
  started?: Promise<unknown>;
  restored?: Promise<unknown>;
  serviceManager: { contents: { save: (path: string, model: object) => Promise<unknown> } };
  commands: { execute: (id: string, args?: object) => Promise<unknown> };
  shell: { widgets: (area: string) => Iterator<LiteWidget & { close?: () => void }>; activateById: (id: string) => void; currentWidget: LiteWidget | null };
};

/** JupyterLite restores the documents from the previous visit once its layout is restored; close them so only the requested notebook is open. */
async function closeOtherDocuments(app: LiteApp): Promise<void> {
  if (app.restored) await app.restored;
  try { await app.commands.execute("application:close-all"); } catch { /* older runtime without the command */ }
  const it = app.shell.widgets("main");
  const open: (LiteWidget & { close?: () => void })[] = [];
  for (let n = it.next(); !n.done; n = it.next()) open.push(n.value);
  for (const w of open) w.close?.();
}

function BrowserRuntime({ source, fileName }: { source: Source; fileName: string }) {
  const mounted = useMounted();
  const frameRef = useRef<HTMLIFrameElement>(null);
  const appRef = useRef<LiteApp | null>(null);
  const [liteState, setLiteState] = useState<"loading" | "ready" | "failed">("loading");
  const liteSrc = "/jupyterlite/lab/index.html?reset";  // ?reset discards the saved workspace, so documents from an earlier visit are not restored

  // The runtime exposes its app on the iframe window (same origin). We fetch the generated notebook with the
  // user's cookies, save it through the runtime's contents API, and open it: a real per-user prefill.
  useEffect(() => {
    if (!mounted) return;
    let cancelled = false;
    let attempts = 0;
    const timer = setInterval(async () => {
      const app = (frameRef.current?.contentWindow as (Window & { jupyterapp?: LiteApp }) | null)?.jupyterapp;
      attempts += 1;
      if (!app) { if (attempts > 180) { clearInterval(timer); setLiteState("failed"); } return; }  // the runtime can take a while on a busy machine
      clearInterval(timer);
      try {
        if (app.started) await app.started;  // the app object appears before its services are ready
        const res = await fetch(`/api/pg${source.path}`);
        const nb = await res.json();
        await closeOtherDocuments(app);
        await app.serviceManager.contents.save(fileName, { type: "notebook", format: "json", content: nb });
        const widget = (await app.commands.execute("docmanager:open", { path: fileName })) as LiteWidget | undefined;
        if (widget?.id) app.shell.activateById(widget.id);
        appRef.current = app;
        // A restore that lands after our open would leave a second, output-less tab: sweep anything that is not our file.
        for (const delay of [1500, 4000]) {
          setTimeout(() => {
            const it = app.shell.widgets("main");
            for (let n = it.next(); !n.done; n = it.next()) {
              const w = n.value as LiteWidget & { close?: () => void; title?: { label?: string } };
              if (w.title?.label && w.title.label !== fileName) w.close?.();
            }
            if (widget?.id) app.shell.activateById(widget.id);
          }, delay);
        }
        if (!cancelled) setLiteState("ready");
      } catch {
        if (!cancelled) setLiteState("failed");
      }
    }, 500);
    return () => { cancelled = true; clearInterval(timer); };
  }, [mounted, source.path, fileName]);

  const runAll = () => {
    const app = appRef.current;
    if (!app) return;
    // Make sure the command acts on our notebook even if the person clicked into the runtime's own UI.
    const it = app.shell.widgets("main");
    for (let n = it.next(); !n.done; n = it.next()) { if ((n.value as { title?: { label?: string } }).title?.label === fileName) { app.shell.activateById(n.value.id); break; } }
    void app.commands.execute("notebook:run-all-cells");
  };

  return (
    <section className="overflow-hidden rounded-2xl border bg-card" aria-label="In-browser notebook">
      <div className="flex items-center justify-between gap-2 border-b px-3 py-2 text-xs text-muted-foreground">
        <span>JupyterLite · Pyodide kernel · {source.label} · <span data-testid="lite-state" className={liteState === "ready" ? "text-brand-emerald" : liteState === "failed" ? "text-brand-rose" : ""}>{liteState === "ready" ? `${fileName} opened` : liteState === "failed" ? "could not open the notebook" : "loading runtime…"}</span></span>
        <span className="flex items-center gap-2">
          <button type="button" onClick={runAll} disabled={liteState !== "ready"} className="inline-flex h-7 items-center gap-1 rounded-md border px-2.5 text-xs hover:border-brand-violet/40 disabled:opacity-50" aria-label="Run all cells in the browser"><Play className="size-3" /> Run all</button>
          <a href={liteSrc} target="_blank" rel="noreferrer" className="text-brand-violet-soft hover:underline">Open full screen</a>
        </span>
      </div>
      {mounted ? <iframe ref={frameRef} title="JupyterLite notebook" src={liteSrc} className="h-[70vh] w-full bg-white" data-testid="jupyterlite-frame" /> : <div className="h-[70vh] w-full animate-pulse bg-muted" aria-hidden />}
    </section>
  );
}

function SandboxRunner({ source, autorun }: { source: Source; autorun: boolean }) {
  const [cells, setCells] = useState<Cell[] | null>(null);
  const [exec, setExec] = useState<ExecResult | null>(null);
  const [running, setRunning] = useState(false);
  const [packages, setPackages] = useState("");
  const [pipOut, setPipOut] = useState<string | null>(null);
  const [scratch, setScratch] = useState(`import playground as pg\npg.hello()\nprint(pg.chat("Say hello in one line."))`);
  const [scratchOut, setScratchOut] = useState<{ stdout: string; stderr: string; exit_code: number; ms: number; backend: string } | null>(null);
  const [scratchRunning, setScratchRunning] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/pg${source.path}`).then((r) => r.json()).then((nb: { cells: Cell[] }) => { if (!cancelled) setCells(nb.cells); }).catch(() => { if (!cancelled) setCells([]); });
    return () => { cancelled = true; };
  }, [source.path]);

  const runNotebook = useCallback(async () => {
    setRunning(true); setExec(null);
    const res = await fetch("/api/pg/v1/notebooks/execute", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ path: source.path, timeout: 300 }) });
    setExec(res.ok ? await res.json() : { ok: false, cells: [], stderr: `Request failed (${res.status})`, exit_code: 1, ms: 0, backend: "?" });
    setRunning(false);
  }, [source.path]);

  useEffect(() => { if (autorun && !started.current) { started.current = true; void runNotebook(); } }, [autorun, runNotebook]);

  const installPackages = async () => {
    const list = packages.split(/[\s,]+/).filter(Boolean);
    if (!list.length) return;
    setPipOut("Installing…");
    const j = await fetch("/api/pg/v1/sandbox/pip", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ packages: list }) }).then((r) => r.json()).catch(() => ({ ok: false, stderr: "Request failed" }));
    setPipOut(j.ok ? `Installed ${list.join(", ")} in ${j.ms} ms. They stay available in your sandbox.` : (j.stderr || j.stdout || "Install failed"));
  };

  const runScratch = async () => {
    setScratchRunning(true);
    const res = await fetch("/api/pg/v1/sandbox/execute", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ code: scratch }) });
    setScratchOut(res.ok ? await res.json() : { stdout: "", stderr: `Request failed (${res.status})`, exit_code: 1, ms: 0, backend: "?" });
    setScratchRunning(false);
  };

  const outputs = new Map((exec?.cells ?? []).map((c) => [c.cell, c]));
  let codeIndex = -1;

  return (
    <section className="rounded-2xl border bg-card p-4" aria-label="Server sandbox">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span>Runs the whole notebook top to bottom in an isolated Python process with your identity. Production uses Azure Container Apps dynamic sessions.</span>
        <Button size="sm" className="glow-violet" onClick={() => void runNotebook()} disabled={running || !cells} aria-label="Run notebook in sandbox">{running ? <Loader2 className="size-3.5 animate-spin" /> : <Play className="size-3.5" />} {running ? "Running…" : "Run notebook"}</Button>
      </div>
      {exec && (
        <p className={cn("mt-2 text-xs", exec.ok ? "text-brand-emerald" : "text-brand-rose")} data-testid="notebook-exec-summary">
          {exec.ok ? `All ${exec.cells.length} code cells ran` : `Stopped at cell ${exec.cells.length} of ${cells?.filter((c) => c.cell_type === "code").length ?? "?"}`} · {exec.ms} ms · backend {exec.backend}{exec.stderr ? ` · ${exec.stderr.slice(0, 200)}` : ""}
        </p>
      )}
      <div className="mt-3 space-y-2" data-testid="notebook-cells">
        {!cells && <p className="text-xs text-muted-foreground">Loading notebook…</p>}
        {cells?.map((c, i) => {
          if (c.cell_type === "markdown") {
            return <div key={i} className="rounded-lg border-l-2 border-brand-violet/40 bg-muted/30 px-3 py-2 text-xs whitespace-pre-wrap text-muted-foreground">{text(c).replace(/^#+\s*/gm, "").replace(/\*\*/g, "")}</div>;
          }
          codeIndex += 1;
          const out = outputs.get(codeIndex);
          return (
            <div key={i} className="rounded-xl border">
              <pre className="overflow-x-auto rounded-t-xl bg-[#0d0d18] p-3 font-mono text-[12px] leading-5 text-slate-100">{text(c)}</pre>
              {out && (
                <div className="rounded-b-xl bg-muted/40 p-3 font-mono text-[11.5px]" data-testid={`cell-output-${codeIndex}`}>
                  {out.stdout && <pre className="whitespace-pre-wrap">{out.stdout}</pre>}
                  {out.error && <pre className="whitespace-pre-wrap text-brand-rose">{out.error}</pre>}
                  {!out.stdout && !out.error && <span className="text-muted-foreground">(no output)</span>}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-5 rounded-xl border p-3">
        <p className="flex items-center gap-1.5 text-xs font-medium"><Package className="size-3.5 text-brand-violet-soft" /> Install packages in your sandbox</p>
        <p className="mt-1 text-[11px] text-muted-foreground">Like an IDE: packages install once into your own environment and stay for later runs. Inside a cell, <code>%pip install</code> does the same.</p>
        <form className="mt-2 flex gap-2" onSubmit={(e) => { e.preventDefault(); void installPackages(); }}>
          <input value={packages} onChange={(e) => setPackages(e.target.value)} placeholder="tabulate rich scikit-learn" aria-label="Packages to install" className="h-8 flex-1 rounded-md border bg-background px-2 font-mono text-xs" />
          <Button size="sm" type="submit" variant="outline">Install</Button>
        </form>
        {pipOut && <p className="mt-2 text-[11px] text-muted-foreground" data-testid="pip-output">{pipOut}</p>}
      </div>

      <div className="mt-5">
        <p className="text-xs font-medium">Scratch cell</p>
        <textarea value={scratch} onChange={(e) => setScratch(e.target.value)} rows={5} aria-label="Sandbox code" className="mt-2 w-full rounded-xl border bg-[#0d0d18] p-3 font-mono text-[12.5px] leading-6 text-slate-100 outline-none" />
        <div className="mt-2 flex justify-end"><Button size="sm" variant="outline" onClick={() => void runScratch()} disabled={scratchRunning} aria-label="Run in sandbox"><Play className="size-3.5" /> {scratchRunning ? "Running…" : "Run"}</Button></div>
        {scratchOut && (
          <div className="mt-2 rounded-xl border bg-muted/40 p-3 font-mono text-[12px]" data-testid="sandbox-output">
            <p className="mb-1 text-[10.5px] text-muted-foreground">exit {scratchOut.exit_code} · {scratchOut.ms} ms · backend {scratchOut.backend}</p>
            {scratchOut.stdout && <pre className="whitespace-pre-wrap">{scratchOut.stdout}</pre>}
            {scratchOut.stderr && <pre className="whitespace-pre-wrap text-brand-rose">{scratchOut.stderr}</pre>}
          </div>
        )}
      </div>
    </section>
  );
}
