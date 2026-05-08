import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"
import Google from "next-auth/providers/google"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Mot de passe", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null
        try {
          const res = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
          })
          if (!res.ok) return null
          const data = await res.json()
          // Récupère les infos utilisateur
          const meRes = await fetch(`${BACKEND_URL}/api/v1/profile/me`, {
            headers: { Authorization: `Bearer ${data.access_token}` },
          })
          const me = meRes.ok ? await meRes.json() : {}
          return {
            id: me.id || "",
            email: me.email || (credentials.email as string),
            name: me.name || "",
            accessToken: data.access_token as string,
            refreshToken: data.refresh_token as string,
          }
        } catch {
          return null
        }
      },
    }),
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async signIn({ user, account }) {
      // Pour Google OAuth : synchronise avec le backend
      if (account?.provider === "google") {
        try {
          const res = await fetch(`${BACKEND_URL}/api/v1/auth/google-signin`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              google_id: account.providerAccountId,
              email: user.email,
              name: user.name,
            }),
          })
          if (!res.ok) return false
          const data = await res.json()
          user.accessToken = data.access_token
          user.refreshToken = data.refresh_token
        } catch {
          return false
        }
      }
      return true
    },
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id
        token.accessToken = user.accessToken
        token.refreshToken = user.refreshToken
      }
      return token
    },
    async session({ session, token }) {
      session.user.id = token.id as string
      session.accessToken = token.accessToken as string
      return session
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
  session: { strategy: "jwt" },
})
