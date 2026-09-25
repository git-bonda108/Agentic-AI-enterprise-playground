import type { Metadata } from "next";
import { entraConfigured, devLoginAllowed } from "@/auth";
import { DEV_USERS } from "@/lib/users";
import { LoginPanel } from "@/components/shell/login-panel";
import { BeamField } from "@/components/motion/beam-field";

export const metadata: Metadata = { title: "Sign in" };

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; error?: string }>;
}) {
  const params = await searchParams;
  return (
    <main className="relative grid min-h-screen lg:grid-cols-[1.15fr_1fr]">
      <section className="relative hidden overflow-hidden bg-[#0a0a14] text-white lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div className="absolute inset-0 grid-bg opacity-40" aria-hidden />
        <div className="absolute -left-32 top-1/3 size-[520px] rounded-full bg-[radial-gradient(circle,rgba(124,58,237,0.35),transparent_60%)] blur-2xl" aria-hidden />
        <div className="absolute right-[-120px] bottom-[-80px] size-[460px] rounded-full bg-[radial-gradient(circle,rgba(6,182,212,0.28),transparent_60%)] blur-2xl" aria-hidden />
        <header className="relative flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-xl gradient-brand animate-gradient-shift shadow-lg shadow-violet-900/40">
            <span className="text-lg font-semibold">✦</span>
          </span>
          <div>
            <p className="text-sm font-medium tracking-wide text-white/90">Enterprise AI Playground</p>
            <p className="text-xs text-white/50">Governed. Multi-model. Agentic.</p>
          </div>
        </header>
        <div className="relative">
          <h1 className="max-w-xl text-4xl font-semibold leading-tight tracking-tight">
            Every model, every framework, every cloud.
            <span className="block gradient-text">One governed place to build.</span>
          </h1>
          <p className="mt-4 max-w-lg text-base text-white/60">
            Explore frontier and open models, run agent blueprints on mock data, and watch every token and dollar in real time.
          </p>
          <div className="mt-10">
            <BeamField />
          </div>
        </div>
        <footer className="relative flex flex-wrap gap-x-6 gap-y-2 text-xs text-white/45">
          <span>Entra ID single sign-on</span>
          <span>Per-user budgets</span>
          <span>Evaluation gates</span>
          <span>Nightly canary</span>
        </footer>
      </section>
      <section className="flex items-center justify-center p-6 sm:p-10">
        <LoginPanel
          next={params.next ?? "/home"}
          error={params.error}
          entraConfigured={entraConfigured}
          devUsers={devLoginAllowed ? DEV_USERS : []}
        />
      </section>
    </main>
  );
}
