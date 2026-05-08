import "next-auth"
import "next-auth/jwt"

declare module "next-auth" {
  interface User {
    accessToken?: string
    refreshToken?: string
  }
  interface Session {
    accessToken: string
    user: {
      id: string
      email: string
      name: string
    }
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    id?: string
    accessToken?: string
    refreshToken?: string
  }
}
