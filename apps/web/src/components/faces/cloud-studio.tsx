"use client";

import { useEffect, useState } from "react";
import { Cloud, Download, ExternalLink, KeyRound, ListChecks, ServerCog, TerminalSquare } from "lucide-react";
import { CopyButton } from "@/components/playground/copy-button";
import type { CloudGuide, CloudInfo, GuideStep, SelfHosting } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

type Option = { id: string; name: string };
type Script = CloudInfo & { script: string; filename: string };
type Props = {
  clouds: CloudInfo[]; modes: Record<string, string>; frameworks: Option[]; blueprints: Option[]; models: Option[];
  selfHosting: SelfHosting | null; initialBlueprint: string; initialCloud: string;
};

const FIT_STYLE: Record<string, string> = {
  "first-class": "bg-brand-emerald/15 text-brand-emerald",
  sample: "bg-brand-cyan/15 text-brand-cyan",
  "bring your own": "bg-amber-500/15 text-amber-400",
  harness: "bg-muted text-muted-foreground",
};

function CommandBlock({ commands, label }: { commands: string[]; label: string }) {
  if (commands.length === 0) return null;
  const text = commands.join("\n");
  return (
    <div className="relative mt-2">
      <pre className="overflow-auto rounded-xl border bg-[#0d0d18] p-3 pr-20 font-mono text-[11.5px] leading-5 text-slate-100">{text}</pre>
      <div className="absolute right-2 top-2"><CopyButton text={text} label={label} /></div>
    </div>
  );
}

function StepCard({ step, external }: { step: Omit<GuideStep, "number"> & { number?: number }; external: boolean }) {
  return (
    <li className="rounded-2xl border bg-card p-4">
      <p className="text-sm font-semibold">{step.number ? `${step.number}. ` : ""}{step.title}</p>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">{step.body}</p>
      <CommandBlock commands={step.commands} label="Copy commands" />
      {step.links.length > 0 && (
        <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
          {step.links.map((l) => (
            l.href.startsWith("http") || external
              ? <a key={l.href + l.label} href={l.href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">{l.label} <ExternalLink className="size-3" /></a>
              : <a key={l.href + l.label} href={l.href.startsWith("/v1/") ? `/api/pg${l.href}` : l.href} className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">{l.label}</a>
          ))}
        </p>
      )}
    </li>
  );
}

function PlatformDetail({ cloud, frameworks }: { cloud: CloudInfo; frameworks: Option[] }) {
  const cli = cloud.cli;
  return (
    <div className="grid gap-4 lg:grid-cols-2" data-testid="platform-detail">
      <section className="rounded-2xl border bg-card p-4">
        <p className="flex items-center gap-2 text-sm font-semibold"><ServerCog className="size-4 text-brand-cyan" /> {cloud.name}</p>
        <p className="mt-1 text-xs text-muted-foreground">{cloud.vendor}. {cloud.runtime}.</p>
        <p className="mt-2 text-xs"><span className="font-medium">Pricing:</span> {cloud.pricing}</p>
        <p className="mt-1 text-xs text-muted-foreground"><span className="font-medium text-foreground">Roles:</span> {cloud.roles}</p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs" data-testid="platform-links">
          <a href={cloud.portal_url} target="_blank" rel="noreferrer" aria-label={`Open ${cloud.portal_label}`} className="inline-flex h-8 items-center gap-1 rounded-lg bg-primary px-3 font-medium text-primary-foreground">Open portal <ExternalLink className="size-3" /></a>
          <a href={cloud.account_url} target="_blank" rel="noreferrer" className="inline-flex h-8 items-center gap-1 rounded-lg border px-3 hover:bg-muted">Account <ExternalLink className="size-3" /></a>
          <a href={cloud.quickstart_url} target="_blank" rel="noreferrer" className="inline-flex h-8 items-center gap-1 rounded-lg border px-3 hover:bg-muted">Quickstart <ExternalLink className="size-3" /></a>
          <a href={cloud.pricing_url} target="_blank" rel="noreferrer" className="inline-flex h-8 items-center gap-1 rounded-lg border px-3 hover:bg-muted">Pricing <ExternalLink className="size-3" /></a>
          <a href={cloud.roles_url} target="_blank" rel="noreferrer" className="inline-flex h-8 items-center gap-1 rounded-lg border px-3 hover:bg-muted">Permissions <ExternalLink className="size-3" /></a>
        </div>
        <p className="mt-4 text-xs font-medium">Framework fit</p>
        <p className="text-[11px] text-muted-foreground">{cloud.frameworks_note}</p>
        <ul className="mt-2 flex flex-wrap gap-1.5" data-testid="framework-fit">
          {frameworks.map((f) => (
            <li key={f.id} className={cn("rounded-full px-2 py-0.5 text-[10.5px] font-medium", FIT_STYLE[cloud.frameworks[f.id]] ?? "bg-muted")}>{f.name}: {cloud.frameworks[f.id]}</li>
          ))}
        </ul>
        <p className="mt-3 text-xs font-medium">Models sold natively</p>
        <p className="text-[11px] text-muted-foreground">{cloud.native_providers.join(", ")}. {cloud.native_note} <a href={cloud.models_url} target="_blank" rel="noreferrer" className="text-brand-violet-soft hover:underline">Model catalog</a></p>
      </section>
      <section className="rounded-2xl border bg-card p-4" data-testid="signin-block">
        <p className="flex items-center gap-2 text-sm font-semibold"><KeyRound className="size-4 text-brand-violet-soft" /> Sign in with the CLI</p>
        <p className="mt-1 text-xs text-muted-foreground">{cli.name}. {cli.login_note}</p>
        <p className="mt-3 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Install</p>
        <ul className="mt-1 space-y-1">
          {cli.install.map((i) => (
            <li key={i.cmd} className="flex items-center justify-between gap-2 rounded-lg border bg-background/60 px-2 py-1 text-[11px]">
              <span className="truncate font-mono"><span className="mr-2 rounded bg-muted px-1 font-sans text-[10px] text-muted-foreground">{i.os}</span>{i.cmd}</span>
              <CopyButton text={i.cmd} />
            </li>
          ))}
        </ul>
        <p className="mt-3 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Sign in</p>
        <CommandBlock commands={cli.login} label="Copy sign-in" />
        <p className="mt-3 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Verify</p>
        <CommandBlock commands={cli.verify} label="Copy verify" />
        <p className="mt-3 flex flex-wrap gap-x-3 text-[11px]">
          <a href={cli.install_docs} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">Install docs <ExternalLink className="size-3" /></a>
          <a href={cli.login_docs} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">Sign-in docs <ExternalLink className="size-3" /></a>
          <a href={cloud.reference_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">CLI reference <ExternalLink className="size-3" /></a>
        </p>
      </section>
    </div>
  );
}

export function CloudStudio({ clouds, modes, frameworks, blueprints, models, selfHosting, initialBlueprint, initialCloud }: Props) {
  const [blueprint, setBlueprint] = useState(initialBlueprint);
  const [cloud, setCloud] = useState(initialCloud);
  const [framework, setFramework] = useState(frameworks[0]?.id ?? "langgraph");
  const [model, setModel] = useState(models[0]?.id ?? "smart");
  const [mode, setMode] = useState<"gateway" | "native">("gateway");
  const [guide, setGuide] = useState<CloudGuide | null>(null);
  const [script, setScript] = useState<Script | null>(null);
  const current = clouds.find((c) => c.id === cloud) ?? clouds[0];

  useEffect(() => {
    let stale = false;
    const q = new URLSearchParams({ blueprint, cloud, framework, model, mode });
    fetch(`/api/pg/v1/clouds/guide?${q.toString()}`).then((r) => (r.ok ? r.json() : null)).then((j) => { if (!stale) setGuide(j); });
    return () => { stale = true; };
  }, [blueprint, cloud, framework, model, mode]);

  useEffect(() => {
    let stale = false;
    fetch(`/api/pg/v1/blueprints/${blueprint}/deploy/${cloud}`).then((r) => (r.ok ? r.json() : null)).then((j) => { if (!stale) setScript(j); });
    return () => { stale = true; };
  }, [blueprint, cloud]);

  const downloadScript = () => {
    if (!script) return;
    const blob = new Blob([script.script], { type: "text/x-shellscript" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = script.filename;
    a.click();
  };
  const guideQuery = new URLSearchParams({ blueprint, cloud, framework, model, mode, download: "1" }).toString();

  return (
    <div className="mx-auto max-w-7xl">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Discover</p>
      <h1 className="text-2xl font-semibold tracking-tight">Cloud platforms</h1>
      <p className="mt-1 text-sm text-muted-foreground">Take any blueprint to a provider runtime. Each platform shows its portal, the CLI sign-in and the pricing unit before you run anything; the guide below walks through sign-in, a local run, the model choice, scaffolding, deployment and clean-up for the framework and model you pick. Spend lands on your cloud bill, not on the playground, unless you keep the model on the gateway.</p>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" data-testid="cloud-cards">
        {clouds.map((c) => (
          <button key={c.id} type="button" onClick={() => setCloud(c.id)} aria-pressed={cloud === c.id} className={cn("card-hover rounded-2xl border bg-card p-3.5 text-left", cloud === c.id && "border-brand-violet/60")}>
            <p className="flex items-center gap-2 text-sm font-semibold"><Cloud className="size-4 text-brand-cyan" /> {c.name}</p>
            <p className="mt-1 text-[11px] text-muted-foreground">{c.runtime}</p>
            <p className="mt-2 text-[11px]"><span className="font-medium">Pricing:</span> {c.pricing}</p>
            <p className="mt-1 text-[11px] text-muted-foreground">Needs: {c.prereq}</p>
          </button>
        ))}
      </div>

      <div className="mt-5">{current && <PlatformDetail cloud={current} frameworks={frameworks} />}</div>

      <section className="mt-8" aria-labelledby="guide-heading">
        <h2 id="guide-heading" className="flex items-center gap-2 text-lg font-semibold tracking-tight"><ListChecks className="size-4 text-brand-emerald" /> Step-by-step deploy guide</h2>
        <p className="mt-1 text-xs text-muted-foreground">Pick the blueprint, the framework project, the model and where the model lives. Every step carries the exact commands and the official page they come from.</p>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <label className="flex items-center gap-2">Blueprint
            <select value={blueprint} onChange={(e) => setBlueprint(e.target.value)} aria-label="Blueprint to deploy" className="h-8 max-w-[16rem] rounded-lg border bg-card px-2">
              {blueprints.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2">Framework
            <select value={framework} onChange={(e) => setFramework(e.target.value)} aria-label="Framework to deploy" className="h-8 rounded-lg border bg-card px-2">
              {frameworks.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2">Model
            <select value={model} onChange={(e) => setModel(e.target.value)} aria-label="Model to deploy with" className="h-8 max-w-[16rem] rounded-lg border bg-card px-2">
              {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
          </label>
          <div role="radiogroup" aria-label="Model mode" className="inline-flex rounded-lg border p-0.5" data-testid="guide-mode">
            {(["gateway", "native"] as const).map((m) => (
              <button key={m} type="button" role="radio" aria-checked={mode === m} onClick={() => setMode(m)} title={modes[m]} className={cn("h-7 rounded-md px-2.5 font-medium", mode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}>
                {m === "gateway" ? "Through the playground gateway" : "Native provider endpoint"}
              </button>
            ))}
          </div>
          <a href={`/api/pg/v1/clouds/guide?${guideQuery}`} className="inline-flex h-8 items-center gap-1 rounded-lg border px-3 font-medium hover:bg-muted" aria-label="Download guide as markdown" data-testid="guide-download"><Download className="size-3.5" /> Download guide</a>
        </div>

        {guide && (
          <div className="mt-4" data-testid="guide">
            <div className="flex flex-wrap items-center gap-2 text-xs" data-testid="guide-summary">
              <span className={cn("rounded-full px-2 py-0.5 text-[10.5px] font-medium", FIT_STYLE[guide.framework_fit] ?? "bg-muted")}>{guide.framework_name}: {guide.framework_fit}</span>
              <span className={cn("rounded-full px-2 py-0.5 text-[10.5px] font-medium", guide.mode === "gateway" ? "bg-brand-violet/15 text-brand-violet-soft" : "bg-brand-cyan/15 text-brand-cyan")}>{guide.mode === "gateway" ? "Gateway mode" : "Native mode"}</span>
              <span className="text-muted-foreground">{guide.model_fit.note}</span>
            </div>
            <p className="mt-2 text-xs text-muted-foreground"><span className="font-medium text-foreground">Cost:</span> {guide.cost}</p>
            <ol className="mt-3 grid gap-3 lg:grid-cols-2" data-testid="guide-steps">
              {guide.steps.map((s) => <StepCard key={s.number} step={s} external={false} />)}
            </ol>
          </div>
        )}
      </section>

      <section className="mt-8" aria-labelledby="script-heading">
        <h2 id="script-heading" className="flex items-center gap-2 text-lg font-semibold tracking-tight"><TerminalSquare className="size-4 text-brand-cyan" /> Deploy script</h2>
        <p className="mt-1 text-xs text-muted-foreground">The short form of the same deployment for {current?.name}: one script, the pricing unit in its header.</p>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <button type="button" onClick={downloadScript} disabled={!script} className="inline-flex h-8 items-center gap-1 rounded-lg bg-primary px-3 font-medium text-primary-foreground disabled:opacity-50" aria-label="Download deploy script"><Download className="size-3.5" /> Download script</button>
          {script && <a href={script.docs} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">{script.name} guide <ExternalLink className="size-3" /></a>}
        </div>
        {script && (
          <div className="relative mt-3">
            <pre className="max-h-[420px] overflow-auto rounded-xl border bg-[#0d0d18] p-4 font-mono text-[12px] leading-6 text-slate-100" data-testid="deploy-script">{script.script}</pre>
            <div className="absolute right-2 top-2"><CopyButton text={script.script} /></div>
          </div>
        )}
      </section>

      {selfHosting && (
        <section className="mt-8" aria-labelledby="self-heading" data-testid="self-hosting">
          <h2 id="self-heading" className="flex items-center gap-2 text-lg font-semibold tracking-tight"><ServerCog className="size-4 text-brand-violet-soft" /> {selfHosting.title}</h2>
          <p className="mt-1 text-xs text-muted-foreground">{selfHosting.intro}</p>
          <p className="mt-1 text-xs text-muted-foreground"><span className="font-medium text-foreground">Cost:</span> {selfHosting.cost} <a href={selfHosting.docs} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">Deployment guide <ExternalLink className="size-3" /></a></p>
          <ol className="mt-3 grid gap-3 lg:grid-cols-2">
            {selfHosting.steps.map((s, i) => <StepCard key={s.title} step={{ ...s, number: i + 1 }} external />)}
          </ol>
        </section>
      )}
    </div>
  );
}
