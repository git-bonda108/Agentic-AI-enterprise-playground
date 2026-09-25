"use server";

import { signIn, signOut } from "@/auth";
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
  await signOut({ redirectTo: "/login" });
}
