import "server-only";
import { auth } from "@/auth";

/** Server-side API base. PLAYGROUND_API_URL is read at runtime; NEXT_PUBLIC_API_URL is the build-time fallback. */
export const API_URL = process.env.PLAYGROUND_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const INTERNAL_KEY = process.env.PLAYGROUND_INTERNAL_KEY ?? "local-internal-key";

/** Identity headers the API trusts, derived from the signed-in session. */
export async function identityHeaders(): Promise<Record<string, string> | null> {
  const session = await auth();
  const u = session?.user;
  if (!u?.email) return null;
  const id = (session as { user: { id?: string } }).user.id ?? u.email;
  return {
    "X-Internal-Key": INTERNAL_KEY,
    "X-User-Id": id,
    "X-User-Email": u.email,
    "X-User-Name": u.name ?? u.email,
    "X-User-Role": u.role ?? "explorer",
    "X-User-Department": u.department ?? "General",
  };
}

/** Server-side fetch to the API on behalf of the current user. Returns null when the API is unreachable. */
export async function apiGet<T>(path: string): Promise<T | null> {
  const headers = await identityHeaders();
  if (!headers) return null;
  try {
    const res = await fetch(`${API_URL}${path}`, { headers, cache: "no-store", signal: AbortSignal.timeout(12000) });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}
