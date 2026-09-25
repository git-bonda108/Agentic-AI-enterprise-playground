import Link from "next/link";
import { Blocks, KeyRound, MessagesSquare } from "lucide-react";
import { BeamField } from "@/components/motion/beam-field";

export function GatewayHero() {
  return (
    <section className="relative overflow-hidden rounded-3xl border bg-[#0a0a14] p-6 text-white sm:p-8">
      <div className="absolute inset-0 grid-bg opacity-30" aria-hidden />
      <div className="absolute -left-24 top-0 size-96 rounded-full bg-[radial-gradient(circle,rgba(124,58,237,0.35),transparent_60%)] blur-2xl" aria-hidden />
      <div className="absolute -right-24 bottom-0 size-96 rounded-full bg-[radial-gradient(circle,rgba(6,182,212,0.25),transparent_60%)] blur-2xl" aria-hidden />
      <div className="relative grid items-center gap-8 lg:grid-cols-[1fr_1.1fr]">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-white/50">Your gateway</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
            Start anywhere. <span className="gradient-text">Everything is governed.</span>
          </h2>
          <p className="mt-3 max-w-md text-sm text-white/65">
            Pick a model, a blueprint or a framework. Every run is metered to you, every dollar is visible, and nothing leaves the policy your admins set.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            <Link href="/build/playground" className="inline-flex h-9 items-center gap-2 rounded-lg bg-white px-3.5 text-sm font-medium text-slate-900 hover:bg-white/90">
              <MessagesSquare className="size-4" /> Open playground
            </Link>
            <Link href="/discover/blueprints" className="inline-flex h-9 items-center gap-2 rounded-lg border border-white/20 bg-white/5 px-3.5 text-sm font-medium text-white hover:bg-white/10">
              <Blocks className="size-4" /> Browse blueprints
            </Link>
            <Link href="/admin/settings" className="inline-flex h-9 items-center gap-2 rounded-lg px-3 text-sm text-white/70 hover:text-white">
              <KeyRound className="size-4" /> Get an API key
            </Link>
          </div>
        </div>
        <BeamField className="justify-self-end" />
      </div>
    </section>
  );
}
