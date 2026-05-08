import axios from "axios"
import { getSession, signOut } from "next-auth/react"

const BASE_URL =
  typeof window !== "undefined"
    ? `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1`
    : `${process.env.BACKEND_URL || "http://localhost:8000"}/api/v1`

export const api = axios.create({ baseURL: BASE_URL })

// Injecte le token Bearer depuis la session NextAuth
api.interceptors.request.use(async (config) => {
  if (typeof window !== "undefined") {
    const session = await getSession()
    if (session?.accessToken) {
      config.headers.Authorization = `Bearer ${session.accessToken}`
    }
  }
  return config
})

// Déconnecte si 401 (token expiré et non-refreshable)
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      await signOut({ callbackUrl: "/login" })
    }
    return Promise.reject(error)
  }
)

export default api
