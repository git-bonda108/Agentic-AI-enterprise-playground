"use client";

import { useEffect, useState } from "react";
import { Download, ExternalLink, FileCode2 } from "lucide-react";
import { CopyButton } from "@/components/playground/copy-button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { FlavorRun, FrameworkInfo } from "@/lib/playground-types";
import { Button } from "@/components/ui/button";
import { Play, Rocket } from "lucide-react";
import { cn } from "@/lib/utils";

type Option = { id: string; name: string };

export function FrameworkStudio({ frameworks, blueprints, initialBlueprint }: { frameworks: FrameworkInfo[]; blueprints: Option[]; initialBlueprint: string }) {
  const [blueprint, setBlueprint] = useState(initialBlueprint);
  const [framework, setFramework] = useState(frameworks[0]?.id ?? "langgraph");
  const [files, setFiles] = useState<Record<string, string>>({});
  const [run, setRun] = useState<FlavorRun | null>(null);
  const [running, setRunning] = useState<"smoke" | "live" | null>(null);
  const runProject = async (mode: "smoke" | "live") => {
    setRunning(mode); setRun(null);
    const res = await fetch(`/api/pg/v1/blueprints/${blueprint}/flavor/${framework}/run`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ mode }) });
    setRun(res.ok ? await res.json() : { mode, ok: false, stdout: "", stderr: `Request failed (${res.status})`, exit_code: 1, installed: false, ms: 0 });
    setRunning(null);
  };

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/pg/v1/blueprints/${blueprint}/flavor/${framework}`).then((r) => (r.ok ? r.json() : { files: {} })).then((j) => { if (!cancelled) setFiles(j.files ?? {}); });
    return () => { cancelled = true; };
  }, [blueprint, framework]);

  const current = frameworks.find((f) => f.id === framework);
  return (
    <div className="mx-auto max-w-7xl">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Discover</p>
      <h1 className="text-2xl font-semibold tracking-tight">Frameworks</h1>
      <p className="mt-1 text-sm text-muted-foreground">The same blueprint rendered as a starter project for each SDK, with an offline smoke test, so you leave with code that runs.</p>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5" data-testid="framework-cards">
        {frameworks.map((f) => (
          <button key={f.id} type="button" onClick={() => setFramework(f.id)} aria-pressed={framework === f.id} className={cn("card-hover rounded-2xl border bg-card p-3.5 text-left", framework === f.id && "border-brand-violet/60")}>
            <p className="text-sm font-semibold">{f.name}</p>
            <p className="mt-1 font-mono text-[10.5px] text-muted-foreground">{f.install}</p>
            <p className="mt-2 text-[11px] text-muted-foreground">Hosted: {f.hosted}</p>
            <p className="mt-1 text-[11px] text-muted-foreground">{f.license}</p>
          </button>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2 text-xs">
        <label className="flex items-center gap-2">Blueprint
          <select value={blueprint} onChange={(e) => setBlueprint(e.target.value)} aria-label="Blueprint to render" className="h-8 rounded-lg border bg-card px-2">
            {blueprints.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </label>
        <a href={`/api/pg/v1/blueprints/${blueprint}/flavor/${framework}/download`} className="inline-flex h-8 items-center gap-1 rounded-lg bg-primary px-3 font-medium text-primary-foreground" aria-label="Download project zip"><Download className="size-3.5" /> Download project</a>
        <Button size="sm" variant="outline" onClick={() => void runProject("smoke")} disabled={running !== null} aria-label="Run smoke test"><Play className="size-3.5" /> {running === "smoke" ? "Running…" : "Run smoke test"}</Button>
        <Button size="sm" variant="outline" onClick={() => void runProject("live")} disabled={running !== null} aria-label="Run live in sandbox" title="Installs the SDK into your sandbox and runs agent.py through the gateway with a short-lived token"><Rocket className="size-3.5" /> {running === "live" ? "Installing and running…" : "Run live in sandbox"}</Button>
        {current && <a href={current.docs} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">{current.name} docs <ExternalLink className="size-3" /></a>}
      </div>

      <div className="mt-4 rounded-2xl border bg-card p-4 text-xs" data-testid="gateway-setup">
        <p className="font-semibold">Runs through the playground gateway</p>
        <p className="mt-1 text-muted-foreground">The project needs no provider key. It reads three environment variables and every call is governed, metered and traced under your token.</p>
        <pre className="mt-2 overflow-x-auto rounded-lg bg-[#0d0d18] p-3 font-mono text-[11px] text-slate-100">{`export PLAYGROUND_BASE_URL=${typeof window !== "undefined" ? window.location.origin.replace(/:3000$/, ":8000") : "http://localhost:8000"}/openai/v1\nexport PLAYGROUND_TOKEN=pgk_...      # Admin → Settings → Personal tokens\nexport PLAYGROUND_MODEL=smart        # or any catalog id\npython agent.py`}</pre>
      </div>
      {run && (
        <div className="mt-3 rounded-2xl border bg-card p-4 text-xs" data-testid="flavor-run-output">
          <p className={run.ok ? "font-medium text-brand-emerald" : "font-medium text-brand-rose"}>{run.mode === "smoke" ? "Smoke test" : "Live run"} {run.ok ? "passed" : "failed"} · exit {run.exit_code} · {run.ms} ms{run.installed ? " · SDK installed in your sandbox" : ""}</p>
          {run.stdout && <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-muted/40 p-3 font-mono text-[11px]">{run.stdout}</pre>}
          {run.stderr && <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded-lg bg-brand-rose/10 p-3 font-mono text-[11px] text-brand-rose">{run.stderr}</pre>}
        </div>
      )}
      {Object.keys(files).length > 0 && (
        <Tabs key={`${blueprint}-${framework}`} defaultValue="agent.py" className="mt-4">
          <TabsList>
            {Object.keys(files).map((name) => <TabsTrigger key={name} value={name}><FileCode2 className="mr-1 size-3" />{name}</TabsTrigger>)}
          </TabsList>
          {Object.entries(files).map(([name, content]) => (
            <TabsContent key={name} value={name}>
              <div className="relative">
                <pre className="max-h-[520px] overflow-auto rounded-xl border bg-[#0d0d18] p-4 font-mono text-[12px] leading-6 text-slate-100" data-testid={`file-${name}`}>{content}</pre>
                <div className="absolute right-2 top-2"><CopyButton text={content} /></div>
              </div>
            </TabsContent>
          ))}
        </Tabs>
      )}
    </div>
  );
}
