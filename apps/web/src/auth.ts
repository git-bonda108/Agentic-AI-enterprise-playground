import NextAuth, { type DefaultSession } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import MicrosoftEntraID from "next-auth/providers/microsoft-entra-id";
import { DEV_PASSWORD, findDevUser, type Role } from "@/lib/users";

declare module "next-auth" {
  interface Session {
    user: { role: Role; department: string } & DefaultSession["user"];
  }
  interface User {
    role?: Role;
    department?: string;
  }
}

type AppClaims = { role?: Role; department?: string };

export const entraConfigured = Boolean(process.env.AUTH_MICROSOFT_ENTRA_ID_ID);
export const devLoginAllowed =
  process.env.ALLOW_DEV_LOGIN === "true" || process.env.NODE_ENV !== "production";

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
    jwt({ token, user }) {
      const claims = token as typeof token & AppClaims;
      if (user) {
        claims.role = user.role ?? "explorer";
        claims.department = user.department ?? "General";
      }
      return claims;
    },
    session({ session, token }) {
      const claims = token as typeof token & AppClaims;
      if (token.sub) session.user.id = token.sub;
      session.user.role = claims.role ?? "explorer";
      session.user.department = claims.department ?? "General";
      return session;
    },
  },
});
