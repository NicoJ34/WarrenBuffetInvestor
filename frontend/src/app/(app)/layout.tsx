import Link from "next/link"
import { auth } from "@/../auth"
import { redirect } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { signOut } from "@/../auth"

const NAV = [
  { href: "/dashboard", label: "Tableau de bord" },
  { href: "/portfolio", label: "Portefeuille" },
  { href: "/allocation", label: "Allocation" },
  { href: "/history", label: "Historique" },
  { href: "/profile", label: "Profil" },
]

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await auth()
  if (!session) redirect("/login")

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/dashboard" className="font-bold text-slate-900 text-sm">
              WB Investor
            </Link>
            <Separator orientation="vertical" className="h-5" />
            <nav className="flex items-center gap-1">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="px-3 py-1.5 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-md transition-colors"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>

          <form
            action={async () => {
              "use server"
              await signOut({ redirectTo: "/login" })
            }}
          >
            <Button variant="ghost" size="sm" type="submit">
              Déconnexion
            </Button>
          </form>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">{children}</main>
    </div>
  )
}
