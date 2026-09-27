import { auth } from "@/auth";

const PUBLIC_PREFIXES = ["/login", "/api/auth", "/api/health"];

export const proxy = auth((req) => {
  const { pathname } = req.nextUrl;
  const isPublic = PUBLIC_PREFIXES.some((p) => pathname.startsWith(p));
  const isLoggedIn = Boolean(req.auth?.user);

  if (!isLoggedIn && !isPublic) {
    const url = new URL("/login", req.nextUrl);
    if (pathname !== "/") url.searchParams.set("next", pathname);
    return Response.redirect(url);
  }
  if (isLoggedIn && pathname.startsWith("/login")) {
    return Response.redirect(new URL("/home", req.nextUrl));
  }
});

export default proxy;

// The API proxy is left out on purpose: its route handler checks the session itself and answers 401 rather than
// redirecting, and running the auth wrapper there would re-issue the rolling session cookie on every background poll,
// which can resurrect a session that was signed out while a poll was in flight.
export const config = {
  matcher: ["/((?!api/pg|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|woff2?)$).*)"],
};
