"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { buttonVariants } from "@/components/ui/button"
import api from "@/lib/api"

interface TickerScore {
  ticker: string
  score_global: number
  recommendation: string
  out_of_circle: boolean
}

interface Position {
  ticker: string
  name: string
  sector: string | null
  country: string | null
  currency: string
  quantity: string
  average_cost: string
  current_price: string | null
  current_value_eur: string | null
  cost_basis_eur: string
  unrealized_pnl_eur: string | null
  unrealized_pnl_pct: number | null
  portfolio_weight: number
  buffett_score: number | null
  recommendation: string | null
}

interface Summary {
  total_value_eur: string
  total_cost_eur: string
  total_pnl_eur: string
  total_pnl_pct: number
  positions_count: number
  sector_allocation: Record<string, number>
  country_allocation: Record<string, number>
}

function fmt(n: string | number, decimals = 2) {
  return Number(n).toLocaleString("fr-FR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

function fmtEur(n: string | number) {
  return Number(n).toLocaleString("fr-FR", { style: "currency", currency: "EUR" })
}

function PnlBadge({ pct }: { pct: number }) {
  const positive = pct >= 0
  return (
    <span className={`text-xs font-medium ${positive ? "text-emerald-600" : "text-red-600"}`}>
      {positive ? "+" : ""}{fmt(pct)}%
    </span>
  )
}

function ScoreBadge({ score, rec }: { score: number; rec: string }) {
  const color = score >= 80 ? "bg-emerald-100 text-emerald-800"
    : score >= 60 ? "bg-blue-100 text-blue-800"
    : score >= 40 ? "bg-amber-100 text-amber-800"
    : "bg-red-100 text-red-800"
  return (
    <div className="flex flex-col items-end gap-0.5">
      <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${color}`}>{Math.round(score)}</span>
      <span className="text-xs text-slate-400 truncate max-w-[100px]">{rec}</span>
    </div>
  )
}

export default function PortfolioPage() {
  const [positions, setPositions] = useState<Position[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [scores, setScores] = useState<Record<string, TickerScore>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const fetchData = async () => {
    setLoading(true)
    setError("")
    try {
      const [posRes, sumRes] = await Promise.all([
        api.get("/portfolio/positions", { timeout: 30000 }),
        api.get("/portfolio/summary", { timeout: 30000 }),
      ])
      setPositions(posRes.data)
      setSummary(sumRes.data)

      // Charge les scores en arrière-plan (non-bloquant)
      api.get("/analysis/portfolio/scores", { timeout: 60000 })
        .then(res => {
          const map: Record<string, TickerScore> = {}
          for (const s of res.data) map[s.ticker] = s
          setScores(map)
        })
        .catch(() => {})
    } catch {
      setError("Impossible de charger le portefeuille — Yahoo Finance est peut-être temporairement indisponible. Réessaie dans quelques minutes.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-slate-400 text-sm">Chargement des cours en temps réel…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-red-500">{error}</p>
        <Button onClick={fetchData} variant="outline" size="sm">Réessayer</Button>
      </div>
    )
  }

  if (positions.length === 0) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-slate-900">Portefeuille</h1>
        <Card>
          <CardContent className="py-12 text-center space-y-3">
            <p className="text-slate-500">Aucune position ouverte</p>
            <Link href="/history" className={buttonVariants()}>
              Saisir ma première transaction
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  const pnlPositive = summary ? Number(summary.total_pnl_eur) >= 0 : true

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Portefeuille</h1>
          <p className="text-slate-500 mt-1">Cours J-1 via Yahoo Finance</p>
        </div>
        <Button onClick={fetchData} variant="outline" size="sm">Actualiser</Button>
      </div>

      {/* Résumé */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Valeur totale</CardDescription>
              <CardTitle className="text-2xl">{fmtEur(summary.total_value_eur)}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-slate-400">{summary.positions_count} position{summary.positions_count > 1 ? "s" : ""}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>P&L latent</CardDescription>
              <CardTitle className={`text-2xl ${pnlPositive ? "text-emerald-600" : "text-red-600"}`}>
                {pnlPositive ? "+" : ""}{fmtEur(summary.total_pnl_eur)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <PnlBadge pct={summary.total_pnl_pct} />
              <span className="text-xs text-slate-400 ml-1">vs coût d&apos;achat</span>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Coût total investi</CardDescription>
              <CardTitle className="text-2xl">{fmtEur(summary.total_cost_eur)}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-slate-400">Prix de revient EUR</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tableau des positions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Positions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-slate-500 text-xs">
                  <th className="text-left py-2 pr-4">Ticker</th>
                  <th className="text-left py-2 pr-4 hidden md:table-cell">Secteur</th>
                  <th className="text-right py-2 pr-4">Qté</th>
                  <th className="text-right py-2 pr-4">PRU</th>
                  <th className="text-right py-2 pr-4">Cours</th>
                  <th className="text-right py-2 pr-4">Valeur EUR</th>
                  <th className="text-right py-2 pr-4">P&L EUR</th>
                  <th className="text-right py-2 pr-4">P&L %</th>
                  <th className="text-right py-2 pr-4">Poids</th>
                  <th className="text-right py-2">Score</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => {
                  const pnlPos = pos.unrealized_pnl_eur == null || Number(pos.unrealized_pnl_eur) >= 0
                  const score = scores[pos.ticker]
                  return (
                    <tr key={pos.ticker} className="border-b border-slate-50 hover:bg-slate-50">
                      <td className="py-3 pr-4">
                        <Link href={`/stocks/${pos.ticker}`} className="font-mono font-semibold hover:text-blue-600 hover:underline">
                          {pos.ticker}
                        </Link>
                        <div className="text-xs text-slate-400 truncate max-w-[120px]">{pos.name}</div>
                      </td>
                      <td className="py-3 pr-4 hidden md:table-cell">
                        {pos.sector ? (
                          <Badge variant="secondary" className="text-xs font-normal">
                            {pos.sector}
                          </Badge>
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      <td className="py-3 pr-4 text-right">{fmt(pos.quantity, 4)}</td>
                      <td className="py-3 pr-4 text-right text-slate-600">
                        {fmt(pos.average_cost)} {pos.currency}
                      </td>
                      <td className="py-3 pr-4 text-right font-medium">
                        {pos.current_price != null ? `${fmt(pos.current_price)} ${pos.currency}` : <span className="text-slate-300">N/D</span>}
                      </td>
                      <td className="py-3 pr-4 text-right font-medium">
                        {pos.current_value_eur != null ? fmtEur(pos.current_value_eur) : <span className="text-slate-300">N/D</span>}
                      </td>
                      <td className={`py-3 pr-4 text-right font-medium ${pnlPos ? "text-emerald-600" : "text-red-600"}`}>
                        {pos.unrealized_pnl_eur != null ? `${pnlPos ? "+" : ""}${fmtEur(pos.unrealized_pnl_eur)}` : <span className="text-slate-300">N/D</span>}
                      </td>
                      <td className="py-3 pr-4 text-right">
                        {pos.unrealized_pnl_pct != null ? <PnlBadge pct={pos.unrealized_pnl_pct} /> : <span className="text-slate-300">N/D</span>}
                      </td>
                      <td className="py-3 pr-4 text-right text-slate-500">
                        {fmt(pos.portfolio_weight)}%
                      </td>
                      <td className="py-3 text-right">
                        {score
                          ? <ScoreBadge score={score.score_global} rec={score.recommendation} />
                          : <span className="text-slate-300 text-xs">…</span>
                        }
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Répartition sectorielle */}
      {summary && Object.keys(summary.sector_allocation).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Répartition sectorielle</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(summary.sector_allocation)
                .sort(([, a], [, b]) => b - a)
                .map(([sector, pct]) => (
                  <div key={sector} className="flex items-center gap-3">
                    <div className="w-36 text-sm text-slate-600 shrink-0 truncate">{sector}</div>
                    <div className="flex-1 bg-slate-100 rounded-full h-2">
                      <div
                        className="bg-slate-700 h-2 rounded-full"
                        style={{ width: `${Math.min(pct, 100)}%` }}
                      />
                    </div>
                    <div className="text-sm font-medium w-12 text-right">{fmt(pct)}%</div>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
