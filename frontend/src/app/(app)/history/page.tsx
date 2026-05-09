"use client"

import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import api from "@/lib/api"

interface Transaction {
  id: string
  ticker: string
  transaction_type: "buy" | "sell"
  quantity: string
  price: string
  currency: string
  transaction_date: string
  exchange: string | null
  notes: string | null
  created_at: string
}

const schema = z.object({
  ticker: z.string().min(1, "Requis").max(20),
  transaction_type: z.enum(["buy", "sell"]),
  quantity: z.number().positive("Doit être positif"),
  price: z.number().positive("Doit être positif"),
  currency: z.string().min(3).max(10),
  transaction_date: z.string().min(1, "Requis"),
  exchange: z.string().optional(),
  notes: z.string().optional(),
})

type FormData = z.infer<typeof schema>

function fmt(n: string | number, decimals = 2) {
  return Number(n).toLocaleString("fr-FR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

export default function HistoryPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      transaction_type: "buy",
      currency: "EUR",
      transaction_date: new Date().toISOString().split("T")[0],
    },
  })

  const txType = watch("transaction_type")

  const fetchTransactions = async () => {
    setLoading(true)
    try {
      const res = await api.get("/portfolio/transactions")
      setTransactions(res.data)
    } catch {
      // silence
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTransactions()
  }, [])

  const onSubmit = async (data: FormData) => {
    setError("")
    setSuccess(false)
    try {
      await api.post("/portfolio/transactions", {
        ...data,
        ticker: data.ticker.toUpperCase(),
      })
      setSuccess(true)
      reset({
        transaction_type: "buy",
        currency: "EUR",
        transaction_date: new Date().toISOString().split("T")[0],
        ticker: "",
        quantity: undefined,
        price: undefined,
        exchange: "",
        notes: "",
      })
      fetchTransactions()
      setTimeout(() => setSuccess(false), 3000)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Erreur lors de l'ajout de la transaction"
      setError(msg)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm("Supprimer cette transaction ?")) return
    setDeleting(id)
    try {
      await api.delete(`/portfolio/transactions/${id}`)
      setTransactions((prev) => prev.filter((tx) => tx.id !== id))
    } catch {
      // silence
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Historique des transactions</h1>
        <p className="text-slate-500 mt-1">Enregistrez vos achats et ventes</p>
      </div>

      {/* Formulaire */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Nouvelle transaction</CardTitle>
        </CardHeader>
        <CardContent>
          {success && (
            <Alert className="mb-4">
              <AlertDescription>Transaction ajoutée avec succès</AlertDescription>
            </Alert>
          )}
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Type achat / vente */}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setValue("transaction_type", "buy")}
                className={`flex-1 py-2 rounded-md text-sm font-medium border transition-colors ${
                  txType === "buy"
                    ? "bg-emerald-600 text-white border-emerald-600"
                    : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                }`}
              >
                Achat
              </button>
              <button
                type="button"
                onClick={() => setValue("transaction_type", "sell")}
                className={`flex-1 py-2 rounded-md text-sm font-medium border transition-colors ${
                  txType === "sell"
                    ? "bg-red-600 text-white border-red-600"
                    : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                }`}
              >
                Vente
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label>Ticker</Label>
                <Input {...register("ticker")} placeholder="AAPL" className="uppercase" />
                {errors.ticker && <p className="text-xs text-red-500">{errors.ticker.message}</p>}
              </div>

              <div className="space-y-1">
                <Label>Date</Label>
                <Input type="date" {...register("transaction_date")} />
                {errors.transaction_date && (
                  <p className="text-xs text-red-500">{errors.transaction_date.message}</p>
                )}
              </div>

              <div className="space-y-1">
                <Label>Quantité</Label>
                <Input type="number" step="0.000001" {...register("quantity", { valueAsNumber: true })} placeholder="10" />
                {errors.quantity && <p className="text-xs text-red-500">{errors.quantity.message}</p>}
              </div>

              <div className="space-y-1">
                <Label>Prix unitaire</Label>
                <Input type="number" step="0.01" {...register("price", { valueAsNumber: true })} placeholder="150.00" />
                {errors.price && <p className="text-xs text-red-500">{errors.price.message}</p>}
              </div>

              <div className="space-y-1">
                <Label>Devise</Label>
                <select
                  {...register("currency")}
                  className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  <option value="EUR">EUR — Euro</option>
                  <option value="USD">USD — Dollar US</option>
                  <option value="GBP">GBP — Livre sterling</option>
                  <option value="CHF">CHF — Franc suisse</option>
                  <option value="JPY">JPY — Yen japonais</option>
                  <option value="CAD">CAD — Dollar canadien</option>
                  <option value="AUD">AUD — Dollar australien</option>
                  <option value="HKD">HKD — Dollar de Hong Kong</option>
                  <option value="SEK">SEK — Couronne suédoise</option>
                  <option value="NOK">NOK — Couronne norvégienne</option>
                  <option value="DKK">DKK — Couronne danoise</option>
                </select>
              </div>

              <div className="space-y-1">
                <Label>Bourse (optionnel)</Label>
                <Input {...register("exchange")} placeholder="XPAR" />
              </div>
            </div>

            <div className="space-y-1">
              <Label>Notes (optionnel)</Label>
              <Input {...register("notes")} placeholder="Remarques…" />
            </div>

            <Button type="submit" disabled={isSubmitting} className="w-full md:w-auto">
              {isSubmitting ? "Enregistrement…" : "Ajouter la transaction"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Liste */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Transactions ({transactions.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-slate-400">Chargement…</p>
          ) : transactions.length === 0 ? (
            <p className="text-sm text-slate-400">Aucune transaction enregistrée</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-slate-500 text-xs">
                    <th className="text-left py-2 pr-4">Date</th>
                    <th className="text-left py-2 pr-4">Ticker</th>
                    <th className="text-left py-2 pr-4">Type</th>
                    <th className="text-right py-2 pr-4">Quantité</th>
                    <th className="text-right py-2 pr-4">Prix</th>
                    <th className="text-right py-2 pr-4">Total</th>
                    <th className="text-left py-2 pr-4">Devise</th>
                    <th className="py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((tx) => {
                    const total = Number(tx.quantity) * Number(tx.price)
                    return (
                      <tr key={tx.id} className="border-b border-slate-50 hover:bg-slate-50">
                        <td className="py-2.5 pr-4 text-slate-500">{tx.transaction_date}</td>
                        <td className="py-2.5 pr-4 font-mono font-medium">{tx.ticker}</td>
                        <td className="py-2.5 pr-4">
                          <Badge
                            variant={tx.transaction_type === "buy" ? "default" : "secondary"}
                            className={
                              tx.transaction_type === "buy"
                                ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-100"
                                : "bg-red-100 text-red-700 hover:bg-red-100"
                            }
                          >
                            {tx.transaction_type === "buy" ? "Achat" : "Vente"}
                          </Badge>
                        </td>
                        <td className="py-2.5 pr-4 text-right">{fmt(tx.quantity, 4)}</td>
                        <td className="py-2.5 pr-4 text-right">{fmt(tx.price)}</td>
                        <td className="py-2.5 pr-4 text-right font-medium">{fmt(total)}</td>
                        <td className="py-2.5 pr-4 text-slate-500">{tx.currency}</td>
                        <td className="py-2.5">
                          <button
                            onClick={() => handleDelete(tx.id)}
                            disabled={deleting === tx.id}
                            className="text-slate-300 hover:text-red-500 transition-colors text-xs"
                          >
                            {deleting === tx.id ? "…" : "✕"}
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
