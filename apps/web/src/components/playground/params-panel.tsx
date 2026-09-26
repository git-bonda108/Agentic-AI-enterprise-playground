"use client";

import { openKeysDrawer } from "@/components/shell/keys-drawer";

import { formatTokens, type CatalogModel, type ChatParams } from "@/lib/playground-types";

export function ParamsPanel({ params, onChange, model }: { params: ChatParams; onChange: (p: ChatParams) => void; model?: CatalogModel }) {
  const per1k = model ? ((model.input_per_m + model.output_per_m) / 2 / 1000).toFixed(4) : null;
  return (
    <aside aria-label="Parameters" className="flex w-[300px] shrink-0 flex-col gap-5 overflow-y-auto border-l bg-sidebar/60 p-4">
      <div>
        <p className="text-[10.5px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">Parameters</p>
        <label className="mt-3 block text-xs">
          <span className="flex justify-between"><span>Temperature</span><span className="font-mono text-muted-foreground">{params.temperature.toFixed(2)}</span></span>
          <input type="range" min={0} max={2} step={0.05} value={params.temperature} onChange={(e) => onChange({ ...params, temperature: Number(e.target.value) })} className="mt-1 w-full accent-[var(--brand-violet)]" aria-label="Temperature" />
        </label>
        <label className="mt-3 block text-xs">
          <span className="flex justify-between"><span>Max output tokens</span><span className="font-mono text-muted-foreground">{params.max_tokens}</span></span>
          <input type="range" min={64} max={16384} step={64} value={params.max_tokens} onChange={(e) => onChange({ ...params, max_tokens: Number(e.target.value) })} className="mt-1 w-full accent-[var(--brand-violet)]" aria-label="Max output tokens" />
        </label>
        <label className="mt-3 block text-xs">
          <span className="flex justify-between"><span>Top p</span><span className="font-mono text-muted-foreground">{params.top_p.toFixed(2)}</span></span>
          <input type="range" min={0} max={1} step={0.01} value={params.top_p} onChange={(e) => onChange({ ...params, top_p: Number(e.target.value) })} className="mt-1 w-full accent-[var(--brand-violet)]" aria-label="Top p" />
        </label>
        <label className="mt-3 block text-xs">
          <span>System prompt</span>
          <textarea
            value={params.system}
            onChange={(e) => onChange({ ...params, system: e.target.value })}
            rows={5}
            placeholder="You are a helpful assistant for our finance team…"
            aria-label="System prompt"
            className="mt-1 w-full resize-y rounded-lg border bg-card p-2 text-xs outline-none focus-visible:border-brand-violet/60"
          />
        </label>
      </div>

      {model && (
        <div className="rounded-xl border bg-card p-3">
          <p className="text-xs font-semibold">{model.name}</p>
          <p className="text-[11px] text-muted-foreground">{model.provider} · {model.tier}</p>
          <dl className="mt-2 grid grid-cols-2 gap-x-2 gap-y-1 text-[11px]">
            <dt className="text-muted-foreground">Input</dt><dd className="font-mono">${model.input_per_m} / 1M</dd>
            <dt className="text-muted-foreground">Output</dt><dd className="font-mono">${model.output_per_m} / 1M</dd>
            {model.cached_input_per_m !== null && (<><dt className="text-muted-foreground">Cached input</dt><dd className="font-mono">${model.cached_input_per_m} / 1M</dd></>)}
            <dt className="text-muted-foreground">Context</dt><dd className="font-mono">{formatTokens(model.context)}</dd>
            <dt className="text-muted-foreground">Blended / 1K</dt><dd className="font-mono">${per1k}</dd>
          </dl>
          <div className="mt-2 flex flex-wrap gap-1">
            {model.tags.map((t) => <span key={t} className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">{t}</span>)}
          </div>
          {!model.available && (
            <p className="mt-2 text-[11px] text-brand-amber">
              No {model.provider} key is available.{" "}
              <button type="button" onClick={() => openKeysDrawer(model.provider)} className="underline">Add your {model.provider} key</button> to use this model.
            </p>
          )}
          {model.available && model.key_source === "personal" && <p className="mt-2 text-[11px] text-brand-violet-soft">Runs on your own {model.provider} key.</p>}
          {model.notes && <p className="mt-2 text-[11px] text-muted-foreground">{model.notes}</p>}
        </div>
      )}
    </aside>
  );
}
