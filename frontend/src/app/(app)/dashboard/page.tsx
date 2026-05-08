import { auth } from "@/../auth"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import Link from "next/link"
import { buttonVariants } from "@/components/ui/button"

export default async function DashboardPage() {
  const session = await auth()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          Bonjour, {session?.user?.name?.split(" ")[0]} 👋
        </h1>
        <p className="text-slate-500 mt-1">Votre tableau de bord d&apos;investissement long terme</p>
      </div>

      {/* Placeholder — sera remplacé en Phase 5 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Valeur du portefeuille</CardDescription>
            <CardTitle className="text-3xl text-slate-400">—</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-slate-400">Disponible après la Phase 2</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Performance totale</CardDescription>
            <CardTitle className="text-3xl text-slate-400">—</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-slate-400">Disponible après la Phase 2</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Score Buffett moyen</CardDescription>
            <CardTitle className="text-3xl text-slate-400">—</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-slate-400">Disponible après la Phase 3</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Commencer</CardTitle>
          <CardDescription>Pour utiliser l&apos;application, commencez par configurer votre profil</CardDescription>
        </CardHeader>
        <CardContent className="flex gap-3">
          <Link href="/profile" className={buttonVariants()}>
            Configurer mon profil
          </Link>
          <Link href="/history" className={buttonVariants({ variant: "outline" })}>
            Saisir une transaction
          </Link>
        </CardContent>
      </Card>
    </div>
  )
}
