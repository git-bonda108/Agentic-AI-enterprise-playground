/**
 * Sign-out epoch: the moment a person signed out, kept in its own cookie.
 *
 * Sessions are stateless JSON Web Tokens, and the auth library refreshes the session cookie on responses it handles.
 * A response that was still in flight when the person signed out can therefore land afterwards and put a valid
 * session cookie back. Recording the sign-out time and treating any session issued before it as signed out closes
 * that window without a server-side session store: the middleware, the app layout and the API proxy all apply it.
 */

export const SIGNED_OUT_AT_COOKIE = "pg_signed_out_at";

/** True when the session was issued after the last sign-out (or no sign-out has been recorded). */
export function sessionIsCurrent(signedInAt: number | undefined, signedOutAt: string | undefined): boolean {
  const epoch = Number(signedOutAt ?? 0);
  if (!Number.isFinite(epoch) || epoch <= 0) return true;
  return (signedInAt ?? 0) > epoch;
}

export const SESSION_COOKIE_NAMES = ["authjs.session-token", "__Secure-authjs.session-token"];
