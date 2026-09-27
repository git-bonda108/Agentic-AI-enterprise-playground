"use client";

import { useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CircleHelp, ExternalLink, X } from "lucide-react";
import { howtoFor } from "@/lib/howto";
import { cn } from "@/lib/utils";

/** A floating "How to" panel for the current page. Remembers whether the person dismissed it, per page, in this browser. */
const EVENT = "playground:howto";
const subscribe = (cb: () => void) => { window.addEventListener(EVENT, cb); window.addEventListener("storage", cb); return () => { window.removeEventListener(EVENT, cb); window.removeEventListener("storage", cb); }; };

export function HowToPanel() {
  const pathname = usePathname();
  return <HowToFor key={pathname} pathname={pathname} />;
}

function HowToFor({ pathname }: { pathname: string }) {
  const howto = howtoFor(pathname);
  const [open, setOpen] = useState(false);
  // Read the dismissed flag from the browser without setting state in an effect; the server snapshot says "seen".
  const seen = useSyncExternalStore(subscribe, () => { try { return localStorage.getItem(`howto:${pathname}`) === "1"; } catch { return true; } }, () => true);

  if (!howto) return null;
  const dismiss = () => { setOpen(false); try { localStorage.setItem(`howto:${pathname}`, "1"); } catch { /* private mode */ } window.dispatchEvent(new Event(EVENT)); };

  return (
    <div className="fixed bottom-4 right-4 z-30 flex flex-col items-end gap-2" data-testid="howto">
      {open && (
        <section className="w-[22rem] max-w-[calc(100vw-2rem)] rounded-2xl border bg-popover p-4 text-popover-foreground shadow-xl" aria-label="How to">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-[10.5px] font-medium uppercase tracking-wider text-muted-foreground">How to</p>
              <h2 className="text-sm font-semibold">{howto.title}</h2>
            </div>
            <button type="button" onClick={dismiss} aria-label="Dismiss how-to" className="rounded-md p-1 text-muted-foreground hover:bg-muted"><X className="size-4" /></button>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">{howto.intro}</p>
          <ol className="mt-2 list-decimal space-y-1.5 pl-4 text-xs">
            {howto.steps.map((s, i) => (
              <li key={i}>{s.text}{s.href && s.label && <> <Link href={s.href} className="text-brand-violet-soft hover:underline">{s.label}</Link></>}</li>
            ))}
          </ol>
          <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
            {howto.docs.map((d) => d.href.startsWith("/") ? <Link key={d.href} href={d.href} className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">{d.label}</Link> : <a key={d.href} href={d.href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">{d.label} <ExternalLink className="size-3" /></a>)}
          </p>
        </section>
      )}
      <button
        type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-label="How to use this page"
        className={cn("inline-flex h-9 items-center gap-1.5 rounded-full border bg-card px-3 text-xs font-medium shadow-md hover:border-brand-violet/50", !seen && !open && "border-brand-violet/60 animate-pulse-glow")}
      >
        <CircleHelp className="size-4 text-brand-violet-soft" /> How to
      </button>
    </div>
  );
}
