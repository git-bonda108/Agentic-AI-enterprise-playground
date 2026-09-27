import { NextResponse, type NextRequest } from "next/server";
import { auth } from "@/auth";
import { SESSION_COOKIE_NAMES, SIGNED_OUT_AT_COOKIE, sessionIsCurrent } from "@/lib/session-epoch";

const PUBLIC_PREFIXES = ["/login", "/api/auth", "/api/health"];

const authed = auth((req) => {
  const { pathname } = req.nextUrl;
  const isPublic = PUBLIC_PREFIXES.some((p) => pathname.startsWith(p));
  const current = sessionIsCurrent(req.auth?.signedInAt, req.cookies.get(SIGNED_OUT_AT_COOKIE)?.value);
  const isLoggedIn = Boolean(req.auth?.user) && current;

  if (!isLoggedIn && !isPublic) {
    const url = new URL("/login", req.nextUrl);
    if (pathname !== "/") url.searchParams.set("next", pathname);
    const res = NextResponse.redirect(url);
    if (req.auth?.user && !current) for (const name of SESSION_COOKIE_NAMES) res.cookies.delete(name);  // a session revived after sign-out
    return res;
  }
  if (isLoggedIn && pathname.startsWith("/login")) {
    return Response.redirect(new URL("/home", req.nextUrl));
  }
});

// Link prefetches are answered without touching the session: the auth wrapper refreshes the rolling session cookie on
// every request it handles, and a prefetch still in flight when a person signs out would otherwise bring the session
// back. The real navigation that follows is checked as usual, and the API proxy answers 401 on its own.
function isPrefetch(req: NextRequest): boolean {
  return req.headers.get("next-router-prefetch") === "1" || req.headers.get("purpose") === "prefetch" || (req.headers.get("sec-purpose") ?? "").includes("prefetch");
}

export function proxy(req: NextRequest, ctx: Parameters<typeof authed>[1]) {
  if (isPrefetch(req)) return NextResponse.next();
  return authed(req, ctx);
}

export default proxy;

// The API proxy is left out on purpose: its route handler checks the session itself and answers 401 rather than
// redirecting, and running the auth wrapper there would re-issue the rolling session cookie on every background poll,
// which can resurrect a session that was signed out while a poll was in flight.
export const config = {
  matcher: ["/((?!api/pg|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|woff2?)$).*)"],
};
