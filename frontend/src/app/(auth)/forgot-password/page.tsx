"use client"

import { useState } from "react"
import Link from "next/link"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import api from "@/lib/api"

const schema = z.object({
  email: z.string().email("Email invalide"),
})

type FormData = z.infer<typeof schema>

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    setLoading(true)
    try {
      await api.post("/auth/forgot-password", { email: data.email })
    } finally {
      setLoading(false)
      setSent(true) // Toujours afficher le message de confirmation (sécurité)
    }
  }

  return (
    <Card>
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold">Mot de passe oublié</CardTitle>
        <CardDescription>Recevez un lien de réinitialisation par email</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {sent ? (
          <Alert>
            <AlertDescription>
              Si un compte existe avec cet email, un lien de réinitialisation vous a été envoyé.
              Vérifiez votre boîte mail (et vos spams).
            </AlertDescription>
          </Alert>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" placeholder="vous@exemple.com" {...register("email")} />
              {errors.email && <p className="text-xs text-red-500">{errors.email.message}</p>}
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Envoi…" : "Envoyer le lien"}
            </Button>
          </form>
        )}

        <p className="text-center text-sm text-slate-500">
          <Link href="/login" className="font-medium text-slate-900 hover:underline">
            Retour à la connexion
          </Link>
        </p>
      </CardContent>
    </Card>
  )
}
