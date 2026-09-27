"use server";

import { cookies } from "next/headers";
import { signIn, signOut } from "@/auth";
import { SIGNED_OUT_AT_COOKIE } from "@/lib/session-epoch";
import { DEV_PASSWORD } from "@/lib/users";

function safeNext(next: unknown): string {
  const value = typeof next === "string" ? next : "/home";
  return value.startsWith("/") && !value.startsWith("//") ? value : "/home";
}

export async function devSignIn(formData: FormData) {
  const email = String(formData.get("email") ?? "");
  const next = safeNext(formData.get("next"));
  await signIn("dev", { email, password: DEV_PASSWORD, redirectTo: next });
}

export async function entraSignIn(formData: FormData) {
  const next = safeNext(formData.get("next"));
  await signIn("microsoft-entra-id", { redirectTo: next });
}

export async function signOutAction() {
  // Any session issued before this moment is treated as signed out, even if a late response re-issues its cookie.
  (await cookies()).set(SIGNED_OUT_AT_COOKIE, String(Date.now()), { httpOnly: true, sameSite: "lax", path: "/", secure: process.env.NODE_ENV === "production" });
  await signOut({ redirectTo: "/login" });
}
