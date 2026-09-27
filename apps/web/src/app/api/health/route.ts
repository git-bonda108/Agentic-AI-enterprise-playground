import { NextResponse } from "next/server";

/** Answers within the liveness probe budget even when the API is unreachable: the API check is short and never throws. */
export async function GET() {
  const apiUrl = process.env.PLAYGROUND_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  let api: "online" | "offline" = "offline";
  try {
    const res = await fetch(`${apiUrl}/health`, { cache: "no-store", signal: AbortSignal.timeout(700) });
    if (res.ok) api = "online";
  } catch {
    api = "offline";
  }
  return NextResponse.json({ web: "online", api, batch: 0 });
}
