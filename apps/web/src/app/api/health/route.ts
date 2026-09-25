import { NextResponse } from "next/server";

export async function GET() {
  const apiUrl = process.env.PLAYGROUND_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  let api: "online" | "offline" = "offline";
  try {
    const res = await fetch(`${apiUrl}/health`, { cache: "no-store", signal: AbortSignal.timeout(1500) });
    if (res.ok) api = "online";
  } catch {
    api = "offline";
  }
  return NextResponse.json({ web: "online", api, batch: 0 });
}
