"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Play } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

export type RunTarget = {
  id: string; name: string; description: string;
  samples: { name: string; input: Record<string, unknown> }[];
  input_schema: Record<string, string>; datasets: string[];
};

/** Shared "start a run" dialog for executable blueprints and runnable catalog entries. */
export function RunDialog({ target, onClose }: { target: RunTarget | null; onClose: () => void }) {
  const router = useRouter();
  const [sample, setSample] = useState(0);
  const [json, setJson] = useState(() => JSON.stringify(target?.samples[0]?.input ?? {}, null, 2));
  const [starting, setStarting] = useState(false);

  const start = async () => {
    if (!target) return;
    let input: Record<string, unknown>;
    try { input = JSON.parse(json); } catch { toast.error("The input is not valid JSON"); return; }
    setStarting(true);
    const res = await fetch("/api/pg/v1/runs", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ blueprint_id: target.id, input }) });
    setStarting(false);
    if (!res.ok) { const d = await res.json().catch(() => ({})); toast.error(d.detail ?? "Could not start the run"); return; }
    const run = await res.json();
    router.push(`/operate/runs/${run.id}`);
  };

  return (
    <Dialog open={target !== null} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="sm:max-w-2xl">
        {target && (
          <>
            <DialogHeader>
              <DialogTitle>Run {target.name}</DialogTitle>
              <DialogDescription>{target.description}</DialogDescription>
            </DialogHeader>
            <div className="grid gap-3 sm:grid-cols-[1fr_1.2fr]">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Sample inputs</p>
                <div className="mt-1 space-y-1" role="radiogroup" aria-label="Sample input">
                  {target.samples.map((s, i) => (
                    <button key={s.name} type="button" role="radio" aria-checked={sample === i} onClick={() => { setSample(i); setJson(JSON.stringify(s.input, null, 2)); }} className={cn("block w-full rounded-lg border px-2.5 py-2 text-left text-xs", sample === i ? "border-brand-violet/60 bg-secondary" : "hover:border-brand-violet/40")}>{s.name}</button>
                  ))}
                </div>
                <p className="mt-3 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Input fields</p>
                <ul className="mt-1 text-[11px] text-muted-foreground">
                  {Object.entries(target.input_schema).map(([k, v]) => <li key={k}><span className="font-mono text-foreground">{k}</span> · {v}</li>)}
                </ul>
                {target.datasets.length > 0 && <p className="mt-3 text-[11px] text-muted-foreground">Knowledge: {target.datasets.join(", ")}</p>}
              </div>
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Input (editable JSON)</p>
                <textarea value={json} onChange={(e) => setJson(e.target.value)} rows={10} aria-label="Run input JSON" className="mt-1 w-full rounded-lg border bg-[#0d0d18] p-2 font-mono text-[12px] text-slate-100 outline-none" />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={onClose}>Cancel</Button>
              <Button className="glow-violet" onClick={start} disabled={starting} aria-label="Start run"><Play className="size-3.5" /> {starting ? "Starting…" : "Start run"}</Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
