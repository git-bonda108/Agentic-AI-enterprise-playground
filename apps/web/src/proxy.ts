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

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|woff2?)$).*)"],
};
