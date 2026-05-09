"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { buttonVariants } from "@/components/ui/button"
import api from "@/lib/api"

interface CriterionDetail {
  score: number
  value: number | string | null
  comment: string
}

interface Analysis {
  ticker: string
  score_date: string
  score_global: number
  score_detail: Record<string, CriterionDetail>
  intrinsic_value: string | null
  safety_margin: number | null
  recommendation: string
  out_of_circle: boolean
}

const CRITERION_LABELS: Record<string, string> = {
  marge_securite: "Marge de sécurité (DCF)",
  roe: "ROE moyen",
  dette: "Ratio dette / CP",
  fcf: "Free Cash Flow",
  dividendes: "Dividendes",
  cercle_competence: "Cercle de compétence",
}

const CRITERION_WEIGHTS: Record<string, string> = {
  marge_securite: "25%",
  roe: "20%",
  fcf: "20%",
  dette: "15%",
  dividendes: "10%",
  cercle_competence: "10%",
}

function ScoreGauge({ score }: { score: number }) {
  const color = score >= 80 ? "#10b981" : score >= 60 ? "#f59e0b" : score >= 40 ? "#f97316" : "#ef4444"
  const radius = 54
  const circumference = Math.PI * radius
  const offset = circumference * (1 - score / 100)

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width="140" height="80" viewBox="0 0 140 80">
        {/* Track */}
        <path
          d="M 10 70 A 60 60 0 0 1 130 70"
          fill="none" stroke="#e2e8f0" strokeWidth="12" strokeLinecap="round"
        />
        {/* Progress */}
        <path
          d="M 10 70 A 60 60 0 0 1 130 70"
          fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
        <text x="70" y="68" textAnchor="middle" fontSize="28" fontWeight="bold" fill={color}>
          {Math.round(score)}
        </text>
        <text x="70" y="82" textAnchor="middle" fontSize="11" fill="#94a3b8">
          / 100
        </text>
      </svg>
    </div>
  )
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 80 ? "bg-emerald-500" : score >= 60 ? "bg-amber-400" : score >= 40 ? "bg-orange-400" : "bg-red-500"
  return (
    <div className="w-full bg-slate-100 rounded-full h-1.5 mt-1">
      <div className={`${color} h-1.5 rounded-full transition-all`} style={{ width: `${score}%` }} />
    </div>
  )
}

function recommendationVariant(rec: string): string {
  if (rec === "Renforcer") return "bg-emerald-100 text-emerald-800"
  if (rec.startsWith("Garder")) return "bg-blue-100 text-blue-800"
  if (rec.startsWith("À surveiller")) return "bg-amber-100 text-amber-800"
  return "bg-red-100 text-red-800"
}

function fmt(n: number | null | undefined, decimals = 2) {
  if (n == null) return "N/D"
  return Number(n).toLocaleString("fr-FR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

export default function StockAnalysisPage() {
  const params = useParams()
  const ticker = (params.ticker as string).toUpperCase()
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    api.get(`/analysis/${ticker}`, { timeout: 30000 })
      .then(res => setAnalysis(res.data))
      .catch(() => setError("Impossible de charger l'analyse. Réessaie dans quelques instants."))
      .finally(() => setLoading(false))
  }, [ticker])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-slate-400 text-sm">Calcul du score Buffett pour {ticker}…</p>
      </div>
    )
  }

  if (error || !analysis) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-red-500">{error}</p>
        <Link href="/portfolio" className={buttonVariants({ variant: "outline", size: "sm" })}>
          Retour au portefeuille
        </Link>
      </div>
    )
  }

  const criteriaOrder = ["marge_securite", "roe", "fcf", "dette", "dividendes", "cercle_competence"]

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900 font-mono">{ticker}</h1>
            {analysis.out_of_circle && (
              <Badge className="bg-amber-100 text-amber-800 text-xs">Hors cercle</Badge>
            )}
          </div>
          <p className="text-slate-500 mt-1 text-sm">Analyse au {analysis.score_date}</p>
        </div>
        <Link href="/portfolio" className={buttonVariants({ variant: "outline", size: "sm" })}>
          ← Portefeuille
        </Link>
      </div>

      {/* Score global */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row items-center gap-6">
            <div className="flex flex-col items-center">
              <ScoreGauge score={analysis.score_global} />
              <p className="text-xs text-slate-400 mt-1">Score Buffett</p>
            </div>
            <div className="flex-1 space-y-3 text-center md:text-left">
              <div className={`inline-flex px-4 py-2 rounded-full text-sm font-semibold ${recommendationVariant(analysis.recommendation)}`}>
                {analysis.recommendation}
              </div>
              {analysis.intrinsic_value && (
                <div className="space-y-1">
                  <p className="text-xs text-slate-500 uppercase tracking-wide">Valeur intrinsèque estimée (DCF)</p>
                  <p className="text-xl font-bold">{fmt(Number(analysis.intrinsic_value))} €/action</p>
                  {analysis.safety_margin !== null && (
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1 bg-slate-100 rounded-full h-2 max-w-[200px]">
                        <div
                          className={`h-2 rounded-full ${analysis.safety_margin >= 0 ? "bg-emerald-500" : "bg-red-500"}`}
                          style={{ width: `${Math.min(Math.abs(analysis.safety_margin), 100)}%` }}
                        />
                      </div>
                      <span className={`text-sm font-medium ${analysis.safety_margin >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                        {analysis.safety_margin >= 0 ? "+" : ""}{fmt(analysis.safety_margin)}% de marge
                      </span>
                    </div>
                  )}
                </div>
              )}
              {!analysis.intrinsic_value && (
                <p className="text-sm text-slate-400">DCF non calculable — données FCF insuffisantes</p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Détail par critère */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Détail par critère</CardTitle>
          <CardDescription>6 critères fondamentaux inspirés de la méthode Buffett</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {criteriaOrder.map(key => {
            const detail = analysis.score_detail[key]
            if (!detail) return null
            return (
              <div key={key} className="space-y-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-700">{CRITERION_LABELS[key]}</span>
                    <span className="text-xs text-slate-400">({CRITERION_WEIGHTS[key]})</span>
                  </div>
                  <span className="text-sm font-bold">{Math.round(detail.score)}/100</span>
                </div>
                <ScoreBar score={detail.score} />
                <p className="text-xs text-slate-500">{detail.comment}</p>
              </div>
            )
          })}
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex gap-3">
        <Link href="/history" className={buttonVariants()}>
          Saisir une transaction
        </Link>
        <Link href="/portfolio" className={buttonVariants({ variant: "outline" })}>
          Retour au portefeuille
        </Link>
      </div>
    </div>
  )
}
