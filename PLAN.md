# Plan d'implémentation — WarrenBuffetInvestor
**Mise à jour :** 8 mai 2026
**Horizon MVP :** 1-2 mois (soirs/week-ends)
**Usage :** Personnel (famille/amis proches)

---

## Décisions d'architecture

### Stack retenue
| Couche | Technologie | Justification |
|---|---|---|
| **Backend** | Python + FastAPI | Compétence principale. Calculs financiers (DCF, scores) naturels en Python. |
| **Frontend** | Next.js 14 (App Router) + Tailwind CSS + shadcn/ui | Composants UI prêts à l'emploi. Le backend fait le travail lourd. |
| **Base de données** | PostgreSQL + SQLAlchemy (ORM Python) | Robuste, relationnel, adapté aux données financières. |
| **Auth** | NextAuth.js (email/password + Google SSO) | Apple SSO reporté en post-MVP. |
| **Données de marché** | `yfinance` (gratuit, MVP) → couche abstraite pour swap vers FMP/Twelve Data | Pas de coûts au départ. |
| **Taux de change** | Open Exchange Rates (free tier) ou `yfinance` pour les paires EUR/* | Mise à jour quotidienne. |
| **Tâches planifiées** | Vercel Cron Jobs | Remplace APScheduler — déclenche les endpoints de mise à jour des cours et fondamentaux. |
| **Hébergement** | Vercel (Next.js + FastAPI serverless) + Supabase (PostgreSQL) | Compte Vercel existant. Supabase free tier (500MB). Quasiment gratuit pour usage perso. |
| **Monorepo** | `/backend` (FastAPI handlers) + `/frontend` (Next.js) + `vercel.json` | FastAPI exposé comme fonctions serverless Python via Vercel. |

### Décisions fonctionnelles
- **Valeur intrinsèque :** DCF simplifié uniquement en V1 (projection FCF sur 10 ans, taux d'actualisation 10%, valeur terminale avec taux de croissance perpétuel paramétrable).
- **Score Buffett :** 6 critères équipondérés (marge de sécurité, ROE/ROIC, dette, FCF, dividendes, cercle de compétence). Pondération ajustable post-MVP.
- **Algo d'allocation :** Version simple d'abord (top N actions par score) → affinage en Phase 4.
- **Devise de référence :** EUR, conversion automatique quotidienne.
- **Apple SSO :** Post-MVP.
- **Import CSV :** Post-MVP (priorité basse pour usage perso).
- **Marchés asiatiques :** Post-MVP Phase 2 (couvre US + Europe en MVP).
- **Notifications :** Aucune en V1 (conforme aux requirements).

---

## Vue d'ensemble des phases

```
Phase 0 : Setup & Architecture        [3-5 jours]
Phase 1 : Auth & Profil utilisateur   [1 semaine]
Phase 2 : Portfolio & Transactions    [2 semaines]
Phase 3 : Analyse Buffett (score DCF) [2 semaines]
Phase 4 : Allocation mensuelle        [1 semaine]
Phase 5 : Dashboard & Visualisations  [1 semaine]
─────────────────────────────────────────────────
MVP total estimé                      ~8 semaines
─────────────────────────────────────────────────
Post-MVP : CSV, Apple SSO, Asie, Mobile
```

---

## Phase 0 — Setup & Architecture (3-5 jours)

### Objectif
Avoir un projet qui tourne localement, avec la structure complète et la base de données initialisée.

### Tâches

#### 0.1 Structure du projet
```
WarrenBuffetInvestor/
├── api/                         # FastAPI handlers — exposés comme fonctions serverless Vercel
│   ├── auth/
│   │   └── [...].py
│   ├── portfolio/
│   │   └── [...].py
│   ├── analysis/
│   │   └── [...].py
│   ├── allocation/
│   │   └── [...].py
│   ├── cron/
│   │   └── update_prices.py     # Déclenché par Vercel Cron Jobs
│   └── _lib/                   # Code partagé : models, services, db, schemas
│       ├── models.py            # SQLAlchemy models
│       ├── schemas.py           # Pydantic schemas
│       ├── db.py                # Connexion Supabase/PostgreSQL
│       └── services/            # Business logic (buffett, dcf, market_data)
├── frontend/ (ou /src/)         # Next.js App Router
│   ├── app/
│   ├── components/              # shadcn/ui components
│   └── lib/                    # API client, NextAuth config
├── vercel.json                  # Routing : /api/* → Python, /* → Next.js
├── requirements.txt             # Dépendances Python (yfinance, sqlalchemy, pydantic…)
└── PLAN.md
```

> **Dev local :** `docker-compose.yml` avec PostgreSQL uniquement (le backend tourne via `uvicorn` localement, Vercel serverless uniquement en prod).

#### 0.2 Schéma base de données (modèles SQLAlchemy)
```
users               — id, email, password_hash, name, created_at
user_profiles       — user_id, competence_circles (JSON), sector_threshold, line_threshold, dcf_discount_rate, dcf_growth_rate
transactions        — id, user_id, ticker, type (buy/sell), quantity, price, currency, date, exchange
positions           — vue calculée (pas de table) ou table matérialisée mise à jour
instruments         — ticker, name, sector, country, currency, exchange, type (stock/ETF)
market_prices       — ticker, date, close_price, currency (cache J-1)
fundamentals        — ticker, date, roe, roic, debt_equity, fcf, fcf_growth, div_yield, div_cagr, updated_at
buffett_scores      — ticker, date, score_global, score_detail (JSON), intrinsic_value
fx_rates            — base_currency, target_currency, date, rate
```

#### 0.3 Configuration
- Variables d'environnement (`.env`) : DATABASE_URL, SECRET_KEY, NEXTAUTH_SECRET, GOOGLE_CLIENT_ID/SECRET
- Docker Compose local : PostgreSQL 16 + FastAPI + Next.js (hot reload)
- Alembic pour les migrations

#### 0.4 Configuration Vercel
- `vercel.json` : routes `/api/*` → Python serverless, tout le reste → Next.js
- Variables d'environnement Vercel : `DATABASE_URL` (Supabase), `NEXTAUTH_SECRET`, `GOOGLE_CLIENT_ID/SECRET`
- Vercel Cron Jobs (dans `vercel.json`) : `0 22 * * *` → `GET /api/cron/update_prices`
- Supabase : créer le projet, récupérer la `DATABASE_URL` (connection pooler Supavisor pour serverless)

#### 0.5 CI basique
- GitHub Actions : lint Python (ruff) + type check (mypy) à chaque push
- Déploiement automatique sur Vercel à chaque push sur `main`

### Livrable
- Dev local : `docker-compose up` (PostgreSQL) + `uvicorn api._lib.main:app` + `next dev` → tout tourne séparément
- Vercel : push sur `main` → déploiement automatique sur `https://warren-buffet-investor.vercel.app`

---

## Phase 1 — Authentification & Profil utilisateur (1 semaine)

### Objectif
Un utilisateur peut s'inscrire, se connecter, et configurer son profil.

### Tâches

#### 1.1 Backend — Auth
- `POST /auth/register` — inscription email/password (bcrypt, validation robustesse mdp)
- `POST /auth/login` — retourne JWT access token + refresh token
- `POST /auth/refresh` — renouvellement du token
- `POST /auth/forgot-password` — envoi email de reset (SMTP ou SendGrid)
- `POST /auth/reset-password` — reset avec token
- Middleware d'authentification sur toutes les routes protégées

#### 1.2 Backend — Profil
- `GET/PUT /profile` — lecture et mise à jour du profil utilisateur
- Champs : nom, cercle de compétence (liste de secteurs), seuil concentration sectorielle (défaut 30%), seuil concentration par ligne (défaut 10%), taux d'actualisation DCF (défaut 10%), taux de croissance perpétuel DCF (défaut 3%)

#### 1.3 Frontend — Auth
- Page `/login` : formulaire email/password + bouton Google SSO
- Page `/register` : formulaire inscription
- Page `/forgot-password` + `/reset-password`
- NextAuth.js configuré (provider Credentials + Google OAuth)
- Redirection automatique vers `/dashboard` si connecté

#### 1.4 Frontend — Profil
- Page `/profile` : édition du cercle de compétence (liste de secteurs à cocher), seuils de concentration, paramètres DCF

### Secteurs disponibles (cercle de compétence)
Technologie, Finance & Banque, Santé & Pharma, Consommation courante, Consommation discrétionnaire, Énergie, Industrie, Matériaux, Immobilier, Télécommunications, Services aux collectivités, ETF

### Livrable
Login Google fonctionnel + profil éditable.

---

## Phase 2 — Portfolio & Transactions (2 semaines)

### Objectif
L'utilisateur peut saisir ses transactions, et voir ses positions calculées en temps réel avec les cours du jour.

### Tâches

#### 2.1 Backend — Couche données marché (abstraite)
- `MarketDataProvider` (interface abstraite Python)
- Implémentation `YFinanceProvider` :
  - `get_price(ticker)` → cours de clôture J-1
  - `get_instrument_info(ticker)` → nom, secteur, pays, devise, exchange
  - `get_fx_rate(from_currency, to_currency)` → taux de change du jour
- Cache en base (`market_prices`, `fx_rates`) pour éviter les appels répétitifs
- Vercel Cron Job `0 22 * * *` → `GET /api/cron/update_prices` : mise à jour des prix toutes les nuits (22h)

#### 2.2 Backend — Instruments
- `GET /instruments/search?q=` — recherche par ticker ou nom (yfinance)
- `GET /instruments/{ticker}` — infos complètes (secteur, pays, devise, exchange)
- Pré-population partielle : S&P 500 + CAC 40 + DAX + FTSE 100 + AEX + Euro Stoxx 50

#### 2.3 Backend — Transactions
- `POST /transactions` — saisie d'une transaction (achat ou vente)
  - Champs : ticker, type, quantity, price, currency, date
  - Validation : quantité > 0, prix > 0, date ≤ aujourd'hui
  - Auto-détection devise et exchange via `get_instrument_info`
- `GET /transactions` — liste paginée, filtrable par ticker/type/date
- `PUT /transactions/{id}` — modification
- `DELETE /transactions/{id}` — suppression

#### 2.4 Backend — Calcul des positions
- `GET /portfolio/positions` — pour chaque ligne :
  - Quantité détenue (somme achats - somme ventes)
  - Prix de revient unitaire moyen pondéré (PUMP)
  - Valeur actuelle (quantité × cours J-1 × taux de change EUR)
  - Plus/moins-value latente absolue (EUR) et en %
  - % du portefeuille total
  - Secteur, pays, devise native
- `GET /portfolio/summary` — valeur totale EUR, P&L total, répartition sectorielle (%), répartition géographique (%)

#### 2.5 Frontend — Saisie transaction
- Page `/transactions/new` : formulaire de saisie avec autocomplétion ticker
- Page `/transactions` : historique avec tri/filtre, actions modifier/supprimer

#### 2.6 Frontend — Vue portefeuille basique
- Page `/portfolio` : tableau des positions (colonnes : ticker, nom, quantité, PUMP, cours actuel, valeur EUR, P&L absolu, P&L %, % du portefeuille, secteur)

### Livrable
Saisir AAPL 10 actions × 150€ → voir la position apparaître avec la valeur actuelle en EUR.

---

## Phase 3 — Analyse Buffett & Score (2 semaines)

### Objectif
Chaque action du portefeuille (et de l'univers) a un score Buffett calculé automatiquement, avec détail et recommandation.

### Tâches

#### 3.1 Backend — Récupération des fondamentaux (yfinance)
- `FundamentalsProvider` utilisant `yfinance.Ticker`:
  - ROE (5 ans) : `financials` + `balance_sheet`
  - ROIC (5 ans) : calculé = NOPAT / Capital investi
  - Ratio dette/capitaux propres : `balance_sheet`
  - FCF (5 ans) et croissance : `cashflow`
  - Dividendes : historique + CAGR 5 ans
  - EPS forward (pour DCF)
- Cache en base (`fundamentals`) — mise à jour trimestrielle (tâche planifiée)

#### 3.2 Backend — Calcul DCF simplifié
```
Paramètres (configurables dans le profil) :
  - Taux d'actualisation (r) : 10% par défaut
  - Taux de croissance perpétuel (g) : 3% par défaut
  - Horizon de projection : 10 ans

Formule :
  FCF_0 = FCF actuel de l'entreprise
  FCF_t = FCF_0 × (1 + croissance_fcf)^t  pour t = 1..10
  Valeur terminale = FCF_10 × (1 + g) / (r - g)
  Valeur intrinsèque = Σ FCF_t / (1+r)^t + VT / (1+r)^10
  Valeur intrinsèque par action = VI / nombre d'actions

Marge de sécurité = (VI_par_action - prix_actuel) / VI_par_action × 100
```

#### 3.3 Backend — Calcul du score Buffett (0-100)
6 critères, chacun noté de 0 à 100, puis moyenne pondérée :

| Critère | Pondération | Logique de scoring |
|---|---|---|
| Marge de sécurité | 25% | >30% → 100 / 15-30% → 70 / 0-15% → 40 / <0 → 0 |
| ROE moyen 5 ans | 20% | >20% → 100 / 15-20% → 80 / 10-15% → 60 / <10% → 20 |
| Ratio dette/CP | 15% | <0.5 → 100 / 0.5-1 → 70 / 1-2 → 40 / >2 → 10 |
| FCF positif & croissance | 20% | FCF positif 5 ans + croissance → 100 / FCF positif stable → 70 / FCF irrégulier → 30 |
| Dividendes réguliers | 10% | CAGR>5% sur 5 ans → 100 / versement régulier → 60 / irrégulier ou absent → 20 |
| Cercle de compétence | 10% | Dans le cercle → 100 / Hors cercle → 0 |

**Recommandation textuelle :**
- 80-100 : Opportunité forte — Renforcer
- 60-79 : Intéressant — Garder / Renforcer prudemment
- 40-59 : À surveiller — Garder
- 0-39 : À éviter / Vendre

#### 3.4 Backend — Endpoints
- `GET /analysis/{ticker}` — score complet + détail par critère + valeur intrinsèque + recommandation
- `GET /portfolio/scores` — scores Buffett de toutes les positions détenues
- Vercel Cron Job `0 23 * * 0` → `GET /api/cron/update_scores` : recalcul des scores chaque dimanche soir

#### 3.5 Frontend — Vue détaillée par action
- Page `/stocks/{ticker}` :
  - Score global (jauge visuelle 0-100)
  - Détail par critère : valeur brute + score individuel + commentaire interprétatif
  - Recommandation textuelle (Renforcer / Garder / Alléger / Vendre)
  - Valeur intrinsèque estimée vs prix actuel (barre de marge de sécurité)
  - Historique des transactions sur cette ligne
  - Avertissement visuel si hors cercle de compétence

#### 3.6 Frontend — Colonne score dans le portefeuille
- Ajouter colonne "Score Buffett" et "Recommandation" dans `/portfolio`

### Livrable
Cliquer sur AAPL → voir son score 72/100 avec détail : ROE 85/100 (ROE moyen 28%), dette 90/100, etc.

---

## Phase 4 — Allocation mensuelle (1 semaine)

### Objectif
L'utilisateur saisit un montant, l'app propose plusieurs répartitions d'achat optimisées selon le score Buffett.

### Tâches

#### 4.1 Backend — Algorithme d'allocation

**Étape 1 — Sélection des candidats**
- Positions existantes avec score ≥ 60 → candidates au renforcement
- Actions de l'univers non détenues avec score ≥ 70 → nouvelles opportunités
- Appliquer le curseur renforcement/nouvelles (ex: 70/30)

**Étape 2 — Répartition idéale**
- Proportionnelle aux scores dans chaque catégorie
- Vérification des contraintes de diversification (seuils sectoriel et par ligne)
- Si contrainte violée → réduire l'allocation et redistribuer

**Étape 3 — Génération de variantes (quantités entières)**
- Calculer quantité = floor(montant_alloué / prix_actuel)
- Générer 3 variantes alternatives par permutations (ex: ajouter 1 action ici, retirer 1 là)
- Pour chaque variante : montant total investi, cash résiduel, score moyen pondéré

**Endpoints**
- `POST /allocation/simulate` — body : `{ amount, reinforcement_ratio, new_opportunities_ratio }`
  - Retourne : 3 propositions de répartition avec détail
- `POST /allocation/confirm` — body : proposition choisie → pré-remplit l'écran de saisie de transaction

#### 4.2 Frontend — Écran allocation mensuelle
- Page `/allocation` :
  - Champ montant mensuel
  - Curseur renforcement vs nouvelles opportunités (70/30 par défaut)
  - Bouton "Calculer"
  - Affichage de 3 cartes-propositions côte à côte :
    - Liste actions + quantités + montant par ligne
    - Montant total investi / Cash résiduel
    - Score moyen pondéré de la répartition
    - Alertes de concentration si déclenchées
  - Bouton "Choisir cette répartition" → pré-remplit le formulaire de transaction

### Livrable
Saisir 500€ → voir 3 propositions : ex. "3 LVMH + 2 MSFT (480€ investi, 20€ résiduel, score moy 78)"

---

## Phase 5 — Dashboard & Visualisations (1 semaine)

### Objectif
Le tableau de bord donne une vue d'ensemble claire et actionnable du portefeuille.

### Tâches

#### 5.1 Backend — Données pour les graphiques
- `GET /portfolio/history?period=1M|3M|6M|1Y|YTD|ALL` — valeur totale du portefeuille par jour (calculée depuis les transactions + prix historiques)
- `GET /portfolio/allocation` — répartition sectorielle et géographique en %
- `GET /portfolio/performance` — performance par période (1M, 3M, 6M, 1Y, YTD, depuis origine)

#### 5.2 Frontend — Dashboard (page d'accueil `/dashboard`)

**Bloc haut :**
- Valeur totale du portefeuille en EUR (grande typo)
- P&L total absolu + %
- Sélecteur de période de performance

**Graphiques (bibliothèque Recharts ou Tremor) :**
- Courbe d'évolution de la valeur du portefeuille
- Donut chart répartition sectorielle (avec alerte si secteur > seuil)
- Donut chart répartition géographique

**Tableau des positions** (version condensée, lien vers `/portfolio` pour le détail) :
- Ticker, nom, valeur EUR, P&L %, score Buffett, recommandation

**Widget allocation :**
- Prochaine allocation (date prévue configurable) → lien vers `/allocation`

#### 5.3 Frontend — Vue portefeuille détaillée `/portfolio`
Tableau complet avec toutes les colonnes + filtres + tri.

#### 5.4 Frontend — Navigation globale
Sidebar / topbar avec : Dashboard, Portefeuille, Allocation, Analyser, Historique, Profil.

### Livrable
Dashboard complet, fonctionnel, responsive mobile. MVP prêt.

---

## Post-MVP — Phase 6+ (sans deadline)

### Fonctionnalités différées (par ordre de priorité)

| Priorité | Feature | Effort |
|---|---|---|
| Haute | Import CSV courtier (mapping colonnes, prévisualisation, dédup) | 1 semaine |
| Haute | Historique des scores Buffett dans le temps (graphique) | 3 jours |
| Haute | Watchlist / Exploration univers (analyser une action sans l'acheter) | 1 semaine |
| Moyenne | Apple SSO | 2 jours |
| Moyenne | Marchés asiatiques (Nikkei, Hang Seng, Topix) | 1 semaine |
| Moyenne | Swap vers fournisseur de données payant (FMP ou Twelve Data) si yfinance insuffisant | 3 jours |
| Moyenne | Pondération personnalisable des critères Buffett | 2 jours |
| Basse | Gordon-Shapiro pour les actions à dividendes | 3 jours |
| Basse | Comparaison portefeuille vs indice de référence | 1 semaine |
| Basse | Applications mobiles natives iOS/Android (Phase 2 requirements) | 2-3 mois |

---

## Points de risque & décisions à anticiper

### Risque 1 — Qualité et disponibilité des données yfinance ⚠️ À REVOIR
`yfinance` est un scraper non officiel, instable pour les fondamentaux (ROIC, FCF historique). En pratique, les appels à l'API Yahoo Finance sont fréquemment bloqués par du rate-limiting (réponse vide, erreur 429), même pour des tickers courants comme MSFT. Constaté en Phase 2 : les cours ne s'affichent pas lors des tests locaux intensifs.

**Mesures déjà en place :**
- Système de cache DB (`market_prices`, `fx_rates`) pour éviter les appels répétés
- Timeout de 8s par appel avec fallback sur le cache
- Affichage N/D en cas d'indisponibilité (ne bloque pas l'interface)

**À revoir avant la mise en production :**
- Évaluer Financial Modeling Prep (FMP) à ~$15/mois comme remplacement principal
- Ou utiliser l'API officielle Yahoo Finance (RapidAPI) avec quota garanti
- La couche abstraite `MarketDataProvider` est prête pour ce swap sans réécriture

### Risque 2 — DCF avec données manquantes
Certaines entreprises n'ont pas de FCF positif ou d'historique suffisant. **Règle :** si FCF manquant ou négatif sur >3 ans, le critère FCF = 0/100 et le score global est signalé "données insuffisantes".

### Risque 3 — Conflit score Buffett vs contrainte de diversification
Un très bon score peut entrer en conflit avec la limite de concentration. **Décision :** la contrainte de diversification prime sur le score (l'utilisateur est averti mais la concentration est bornée).

### Risque 4 — Performance du tableau de bord (<2s)
Le calcul de la valeur historique du portefeuille peut être coûteux. **Solution :** pré-calculer et stocker la valeur quotidienne du portefeuille via la tâche planifiée nocturne.

---

## Résumé des choix ouverts (à décider pendant l'implémentation)

| Décision | Options | Moment de décision |
|---|---|---|
| Fournisseur de données | yfinance (MVP) → FMP/Twelve Data si besoin | Fin Phase 2, si qualité insuffisante |
| Montant minimum par ligne (algo allocation) | 50€ / paramétrable / pas de minimum | Début Phase 4 |
| Nombre max de lignes par allocation | 3 / 5 / paramétrable | Début Phase 4 |
| Bibliothèque graphiques frontend | Recharts / Tremor / Chart.js | Début Phase 5 |
| Hébergement | Vercel + Supabase ✅ décidé | — |
