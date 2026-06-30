import NextAuth, { type NextAuthConfig } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import Google from "next-auth/providers/google";

import type { AuthTokens, User } from "@/types";

declare module "next-auth" {
  interface Session {
    accessToken: string;
    refreshToken: string;
    user: User;
    error?: string;
  }
  interface JWT {
    accessToken: string;
    refreshToken: string;
    userId: string;
    role: string;
  }
}

const config: NextAuthConfig = {
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;
        // Use INTERNAL_API_URL for server-side calls (Docker internal network).
        // Falls back to NEXT_PUBLIC_API_URL for local dev without Docker.
        const base =
          process.env["INTERNAL_API_URL"] ??
          process.env["NEXT_PUBLIC_API_URL"] ??
          "http://localhost:8000";
        try {
          const res = await fetch(`${base}/api/v1/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
          });
          if (!res.ok) return null;
          const tokens = (await res.json()) as AuthTokens;
          return {
            id: "pending",
            accessToken: tokens.access_token,
            refreshToken: tokens.refresh_token,
          };
        } catch {
          return null;
        }
      },
    }),
    Google({
      clientId: process.env["GOOGLE_CLIENT_ID"] ?? "",
      clientSecret: process.env["GOOGLE_CLIENT_SECRET"] ?? "",
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user && "accessToken" in user && "refreshToken" in user) {
        token["accessToken"] = user["accessToken"] as string;
        token["refreshToken"] = user["refreshToken"] as string;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token["accessToken"] as string;
      session.refreshToken = token["refreshToken"] as string;
      return session;
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
  session: { strategy: "jwt" },
};

export const { handlers, auth, signIn, signOut } = NextAuth(config);
