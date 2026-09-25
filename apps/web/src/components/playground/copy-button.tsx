"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      aria-label={label}
      onClick={async () => {
        try { await navigator.clipboard.writeText(text); setDone(true); setTimeout(() => setDone(false), 1500); } catch { /* clipboard blocked */ }
      }}
      className="inline-flex h-7 items-center gap-1 rounded-md border bg-card px-2 text-[11px] text-muted-foreground hover:text-foreground"
    >
      {done ? <Check className="size-3 text-brand-emerald" /> : <Copy className="size-3" />} {done ? "Copied" : label}
    </button>
  );
}
