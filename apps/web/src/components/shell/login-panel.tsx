"use client";

import { motion } from "framer-motion";
import { Building2, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { devSignIn, entraSignIn } from "@/app/login/actions";
import { ROLE_LABEL, type DevUser } from "@/lib/users";

export function LoginPanel({
  next,
  error,
  entraConfigured,
  devUsers,
}: {
  next: string;
  error?: string;
  entraConfigured: boolean;
  devUsers: DevUser[];
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.2, 0.8, 0.2, 1] }}
      className="w-full max-w-md"
    >
      <div className="mb-8 flex items-center gap-3 lg:hidden">
        <span className="grid size-9 place-items-center rounded-lg gradient-brand text-white">✦</span>
        <span className="font-medium">Enterprise AI Playground</span>
      </div>
      <h2 className="text-2xl font-semibold tracking-tight">Sign in</h2>
      <p className="mt-1 text-sm text-muted-foreground">Use your organization account. Every session is governed, metered and auditable.</p>

      {error ? (
        <p role="alert" className="mt-4 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          Sign-in did not complete ({error}). Try again.
        </p>
      ) : null}

      {entraConfigured ? (
        <form action={entraSignIn} className="mt-6">
          <input type="hidden" name="next" value={next} />
          <Button type="submit" size="lg" className="w-full gap-2 glow-violet">
            <Building2 className="size-4" /> Continue with Microsoft Entra ID
          </Button>
        </form>
      ) : (
        <div className="mt-6 rounded-lg border border-dashed px-3 py-2 text-xs text-muted-foreground">
          <KeyRound className="mr-1 inline size-3.5" /> Entra ID is not configured yet. Set the AUTH_MICROSOFT_ENTRA_ID variables to enable single sign-on.
        </div>
      )}

      {devUsers.length > 0 ? (
        <div className="mt-8">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Seeded users for this environment</p>
            <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-medium text-secondary-foreground">demo</span>
          </div>
          <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {devUsers.map((u, i) => (
              <motion.li
                key={u.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 * i, duration: 0.3 }}
              >
                <form action={devSignIn}>
                  <input type="hidden" name="email" value={u.email} />
                  <input type="hidden" name="next" value={next} />
                  <button
                    type="submit"
                    aria-label={`Sign in as ${u.name}`}
                    className="card-hover flex w-full items-center gap-3 rounded-xl border bg-card px-3 py-2.5 text-left"
                  >
                    <span
                      className="grid size-9 shrink-0 place-items-center rounded-full text-xs font-semibold text-white"
                      style={{ background: `linear-gradient(135deg, hsl(${u.hue} 80% 55%), hsl(${(u.hue + 40) % 360} 80% 45%))` }}
                      aria-hidden
                    >
                      {u.initials}
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium">{u.name}</span>
                      <span className="block truncate text-xs text-muted-foreground">{ROLE_LABEL[u.role]} · {u.department}</span>
                    </span>
                  </button>
                </form>
              </motion.li>
            ))}
          </ul>
        </div>
      ) : null}
    </motion.div>
  );
}
