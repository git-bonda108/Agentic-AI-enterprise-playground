import { API_URL, identityHeaders } from "@/lib/api-server";

/** Authenticated proxy from the browser to the API. Streams SSE bodies through untouched. */
async function proxy(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  const headers = await identityHeaders();
  if (!headers) return new Response(JSON.stringify({ detail: "Not signed in" }), { status: 401, headers: { "content-type": "application/json" } });
  const { path } = await ctx.params;
  const url = new URL(req.url);
  const target = `${API_URL}/${path.join("/")}${url.search}`;
  const init: RequestInit & { duplex?: "half" } = {
    method: req.method,
    headers: { ...headers, "content-type": req.headers.get("content-type") ?? "application/json", accept: req.headers.get("accept") ?? "application/json" },
    cache: "no-store",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }
  let upstream: Response;
  try {
    upstream = await fetch(target, init);
  } catch {
    return new Response(JSON.stringify({ detail: "API unreachable" }), { status: 502, headers: { "content-type": "application/json" } });
  }
  const out = new Headers();
  const ct = upstream.headers.get("content-type");
  if (ct) out.set("content-type", ct);
  out.set("cache-control", "no-store");
  if (ct?.includes("text/event-stream")) out.set("x-accel-buffering", "no");
  return new Response(upstream.body, { status: upstream.status, headers: out });
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };
