import NextAuth, { type DefaultSession } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import Google from "next-auth/providers/google";
import MicrosoftEntraID from "next-auth/providers/microsoft-entra-id";
import Okta from "next-auth/providers/okta";
import { DEV_PASSWORD, findDevUser, type Role } from "@/lib/users";

declare module "next-auth" {
  interface Session {
    user: { role: Role; department: string } & DefaultSession["user"];
    /** When this session was issued, compared with the sign-out epoch cookie (see lib/session-epoch). */
    signedInAt?: number;
  }
  interface User {
    role?: Role;
    department?: string;
  }
}

type AppClaims = { role?: Role; department?: string; signedInAt?: number };

export const entraConfigured = Boolean(process.env.AUTH_MICROSOFT_ENTRA_ID_ID);
const googleConfigured = Boolean(process.env.AUTH_GOOGLE_ID);
const oktaConfigured = Boolean(process.env.AUTH_OKTA_ID);
const oidcConfigured = Boolean(process.env.AUTH_OIDC_ISSUER && process.env.AUTH_OIDC_ID);

/** Single sign-on providers available on this deployment, in the order the sign-in page shows them. */
export const ssoProviders: { id: string; name: string }[] = [
  ...(entraConfigured ? [{ id: "microsoft-entra-id", name: "Microsoft Entra ID" }] : []),
  ...(googleConfigured ? [{ id: "google", name: "Google Workspace" }] : []),
  ...(oktaConfigured ? [{ id: "okta", name: "Okta" }] : []),
  ...(oidcConfigured ? [{ id: "oidc", name: process.env.AUTH_OIDC_NAME || "Company sign-in" }] : []),
];
export const ssoConfigured = ssoProviders.length > 0;

/** Seeded pilot accounts are for environments without single sign-on; ALLOW_DEV_LOGIN=true keeps them alongside SSO on purpose. */
export const devLoginAllowed =
  process.env.ALLOW_DEV_LOGIN === "true" || (process.env.NODE_ENV !== "production" && !ssoConfigured);

const list = (value: string | undefined) => (value ?? "").split(",").map((v) => v.trim().toLowerCase()).filter(Boolean);
const allowedDomains = list(process.env.AUTH_ALLOWED_DOMAINS);
const allowedEmails = list(process.env.AUTH_ALLOWED_EMAILS);
const adminEmails = list(process.env.AUTH_ADMIN_EMAILS);
const defaultRole = (process.env.AUTH_DEFAULT_ROLE as Role | undefined) ?? "explorer";

/** Who may sign in through single sign-on: any account of the identity provider unless domains or e-mails are listed. */
export function ssoAllowed(email: string | null | undefined): boolean {
  const e = (email ?? "").toLowerCase();
  if (!e) return false;
  if (allowedDomains.length === 0 && allowedEmails.length === 0) return true;
  return allowedEmails.includes(e) || allowedDomains.includes(e.split("@")[1] ?? "");
}

/** Role and department for a person arriving through single sign-on: admins by e-mail, everyone else the default role; the department is the e-mail domain until an admin changes it. */
export function ssoIdentity(email: string | null | undefined): { role: Role; department: string } {
  const e = (email ?? "").toLowerCase();
  return { role: adminEmails.includes(e) ? "admin" : defaultRole, department: process.env.AUTH_DEFAULT_DEPARTMENT || (e.split("@")[1] ?? "General") };
}

const devSecret = process.env.NODE_ENV !== "production" ? "playground-dev-secret-not-for-production" : undefined;

export const { handlers, auth, signIn, signOut } = NextAuth({
  secret: process.env.AUTH_SECRET ?? devSecret,
  trustHost: true,
  session: { strategy: "jwt" },
  pages: { signIn: "/login" },
  providers: [
    ...(entraConfigured
      ? [
          MicrosoftEntraID({
            clientId: process.env.AUTH_MICROSOFT_ENTRA_ID_ID,
            clientSecret: process.env.AUTH_MICROSOFT_ENTRA_ID_SECRET,
            issuer: process.env.AUTH_MICROSOFT_ENTRA_ID_ISSUER,
          }),
        ]
      : []),
    ...(googleConfigured ? [Google({ clientId: process.env.AUTH_GOOGLE_ID, clientSecret: process.env.AUTH_GOOGLE_SECRET })] : []),
    ...(oktaConfigured ? [Okta({ clientId: process.env.AUTH_OKTA_ID, clientSecret: process.env.AUTH_OKTA_SECRET, issuer: process.env.AUTH_OKTA_ISSUER })] : []),
    ...(oidcConfigured
      ? [
          {
            id: "oidc",
            name: process.env.AUTH_OIDC_NAME || "Company sign-in",
            type: "oidc" as const,
            issuer: process.env.AUTH_OIDC_ISSUER,
            clientId: process.env.AUTH_OIDC_ID,
            clientSecret: process.env.AUTH_OIDC_SECRET,
            authorization: { params: { scope: "openid profile email" } },
          },
        ]
      : []),
    ...(devLoginAllowed
      ? [
          Credentials({
            id: "dev",
            name: "Development users",
            credentials: {
              email: { label: "Email", type: "email" },
              password: { label: "Password", type: "password" },
            },
            authorize: async (credentials) => {
              const user = findDevUser(String(credentials?.email ?? ""));
              if (!user || String(credentials?.password ?? "") !== DEV_PASSWORD) return null;
              return {
                id: user.id,
                name: user.name,
                email: user.email,
                image: null,
                role: user.role,
                department: user.department,
              };
            },
          }),
        ]
      : []),
  ],
  callbacks: {
    signIn({ user, account }) {
      // Seeded pilot accounts are checked by the credentials provider; single sign-on accounts by the allow-list.
      if (account?.provider === "dev") return true;
      return ssoAllowed(user.email);
    },
    jwt({ token, user, account }) {
      const claims = token as typeof token & AppClaims;
      if (user) {
        const fromSso = account?.provider && account.provider !== "dev" ? ssoIdentity(user.email) : null;
        claims.role = user.role ?? fromSso?.role ?? "explorer";
        claims.department = user.department ?? fromSso?.department ?? "General";
        claims.signedInAt = Date.now();
      }
      return claims;
    },
    session({ session, token }) {
      const claims = token as typeof token & AppClaims;
      if (token.sub) session.user.id = token.sub;
      session.user.role = claims.role ?? "explorer";
      session.user.department = claims.department ?? "General";
      session.signedInAt = claims.signedInAt;
      return session;
    },
  },
});
