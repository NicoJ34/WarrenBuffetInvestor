"use client"

import { useEffect, useState } from "react"
import { useForm, Controller } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Slider } from "@/components/ui/slider"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import api from "@/lib/api"

const SECTORS = [
  "Technologie",
  "Finance & Banque",
  "Santé & Pharma",
  "Consommation courante",
  "Consommation discrétionnaire",
  "Énergie",
  "Industrie",
  "Matériaux",
  "Immobilier",
  "Télécommunications",
  "Services aux collectivités",
  "ETF",
]

const schema = z.object({
  competence_circles: z.array(z.string()),
  sector_threshold: z.number().min(10).max(100),
  line_threshold: z.number().min(5).max(50),
  dcf_discount_rate: z.number().min(5).max(20),
  dcf_terminal_growth_rate: z.number().min(0).max(10),
})

type FormData = z.infer<typeof schema>

export default function ProfilePage() {
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const { control, handleSubmit, reset, watch, formState: { isDirty } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      competence_circles: [],
      sector_threshold: 30,
      line_threshold: 10,
      dcf_discount_rate: 10,
      dcf_terminal_growth_rate: 3,
    },
  })

  useEffect(() => {
    api.get("/profile").then((res) => reset(res.data)).catch(() => {})
  }, [reset])

  const onSubmit = async (data: FormData) => {
    setError("")
    setSuccess(false)
    setLoading(true)
    try {
      await api.put("/profile", data)
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Erreur lors de la mise à jour du profil"
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const circles = watch("competence_circles")
  const sectorThreshold = watch("sector_threshold")
  const lineThreshold = watch("line_threshold")
  const discountRate = watch("dcf_discount_rate")
  const growthRate = watch("dcf_terminal_growth_rate")

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Mon profil</h1>
        <p className="text-slate-500 mt-1">Configurez vos préférences d&apos;investissement</p>
      </div>

      {success && (
        <Alert>
          <AlertDescription>Profil mis à jour avec succès</AlertDescription>
        </Alert>
      )}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Cercle de compétence */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Cercle de compétence</CardTitle>
            <CardDescription>
              Sélectionnez les secteurs que vous comprenez suffisamment pour évaluer des entreprises.
              Les actions hors cercle seront signalées visuellement.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              {SECTORS.map((sector) => (
                <Controller
                  key={sector}
                  control={control}
                  name="competence_circles"
                  render={({ field }) => (
                    <div className="flex items-center gap-2">
                      <Checkbox
                        id={sector}
                        checked={field.value.includes(sector)}
                        onCheckedChange={(checked) => {
                          field.onChange(
                            checked
                              ? [...field.value, sector]
                              : field.value.filter((s) => s !== sector)
                          )
                        }}
                      />
                      <label htmlFor={sector} className="text-sm cursor-pointer">
                        {sector}
                      </label>
                    </div>
                  )}
                />
              ))}
            </div>
            {circles.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1">
                {circles.map((s) => (
                  <Badge key={s} variant="secondary">{s}</Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Seuils de concentration */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Seuils de diversification</CardTitle>
            <CardDescription>
              L&apos;application vous alerte si une allocation dépasse ces seuils.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Concentration sectorielle max.</Label>
                <span className="text-sm font-medium">{sectorThreshold}%</span>
              </div>
              <Controller
                control={control}
                name="sector_threshold"
                render={({ field }) => (
                  <Slider
                    min={10} max={100} step={5}
                    value={[field.value]}
                    onValueChange={(v) => field.onChange(Array.isArray(v) ? v[0] : v)}
                  />
                )}
              />
            </div>

            <Separator />

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Concentration par ligne max.</Label>
                <span className="text-sm font-medium">{lineThreshold}%</span>
              </div>
              <Controller
                control={control}
                name="line_threshold"
                render={({ field }) => (
                  <Slider
                    min={5} max={50} step={1}
                    value={[field.value]}
                    onValueChange={(v) => field.onChange(Array.isArray(v) ? v[0] : v)}
                  />
                )}
              />
            </div>
          </CardContent>
        </Card>

        {/* Paramètres DCF */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Paramètres DCF</CardTitle>
            <CardDescription>
              Ces valeurs servent au calcul de la valeur intrinsèque (DCF simplifié sur 10 ans).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <Label>Taux d&apos;actualisation</Label>
                  <p className="text-xs text-slate-400">Rendement minimum attendu (10% = référence Buffett)</p>
                </div>
                <span className="text-sm font-medium">{discountRate}%</span>
              </div>
              <Controller
                control={control}
                name="dcf_discount_rate"
                render={({ field }) => (
                  <Slider
                    min={5} max={20} step={0.5}
                    value={[field.value]}
                    onValueChange={(v) => field.onChange(Array.isArray(v) ? v[0] : v)}
                  />
                )}
              />
            </div>

            <Separator />

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <Label>Taux de croissance perpétuel</Label>
                  <p className="text-xs text-slate-400">Croissance après la période de projection</p>
                </div>
                <span className="text-sm font-medium">{growthRate}%</span>
              </div>
              <Controller
                control={control}
                name="dcf_terminal_growth_rate"
                render={({ field }) => (
                  <Slider
                    min={0} max={10} step={0.5}
                    value={[field.value]}
                    onValueChange={(v) => field.onChange(Array.isArray(v) ? v[0] : v)}
                  />
                )}
              />
            </div>
          </CardContent>
        </Card>

        <Button type="submit" disabled={loading || !isDirty} className="w-full md:w-auto">
          {loading ? "Enregistrement…" : "Enregistrer les modifications"}
        </Button>
      </form>
    </div>
  )
}
