
# Document de Requirements Fonctionnel
## Application web d'aide à l'investissement long terme (approche Buffett)

**Version :** 1.0 — **Date :** 8 mai 2026 — **Auteur :** Nicolas

---

## 1. Vision et objectifs

### 1.1 Vision produit
Une web application permettant à un investisseur particulier de gérer un portefeuille d'actions et d'ETF dans une optique long terme, en s'appuyant sur les principes d'investissement de Warren Buffett. L'outil n'a pas vocation à faire du trading court terme : il accompagne des décisions d'investissement à fréquence mensuelle.

### 1.2 Objectifs fonctionnels
- Permettre d'allouer une somme fixe mensuelle dans des actions selon une logique long terme.
- Fournir une analyse automatisée selon des critères Buffett standardisés pour chaque action.
- Suivre l'évolution du portefeuille avec une vue claire de la performance.
- Aider à la décision d'achat (sur quoi investir le montant mensuel) et de conservation/vente (sur les positions existantes).

### 1.3 Hors périmètre
- Trading haute fréquence ou intraday.
- Exécution réelle des ordres de bourse (l'application est un outil d'aide à la décision, pas un courtier).
- Conseil financier personnalisé au sens réglementaire.
- Suivi de fiscalité et de frais de courtage.

---

## 2. Utilisateurs et accès

### 2.1 Profil utilisateur cible
Investisseur particulier, basé en zone euro, pratiquant un investissement programmé mensuel, avec une orientation long terme et value investing.

### 2.2 Gestion des utilisateurs
- L'application est **multi-utilisateurs** : plusieurs personnes (famille, amis) peuvent disposer chacune de leur compte.
- Chaque utilisateur a son propre portefeuille et ses propres données, strictement cloisonnés.

### 2.3 Authentification
- **Email + mot de passe** avec règles de robustesse standards.
- **SSO Google** et **SSO Apple** comme alternatives.
- Récupération de mot de passe par email.
- Session persistante avec déconnexion possible.

### 2.4 Supports
- **Phase 1** : application web responsive accessible depuis n'importe quel navigateur (desktop, tablette, mobile).
- **Phase 2** (ultérieure) : applications mobiles natives iOS/Android.

---

## 3. Données financières

### 3.1 Marchés couverts
- Marchés américains (NYSE, NASDAQ).
- Marchés européens (Euronext Paris, Amsterdam, Bruxelles, Lisbonne, Frankfurt, Londres, Milan, Madrid).
- Principaux marchés asiatiques (Tokyo, Hong Kong, Shanghai, Shenzhen, Séoul, Singapour).

### 3.2 Instruments couverts
Actions cotées et ETF.

### 3.3 Univers d'analyse
L'application couvre les indices majeurs de référence :
- États-Unis : S&P 500, NASDAQ 100, Dow Jones.
- Europe : CAC 40, SBF 120, DAX, FTSE 100, AEX, Euro Stoxx 50.
- Asie : Nikkei 225, Hang Seng, Topix.

L'utilisateur peut analyser n'importe quelle action de ces indices, ainsi que les principaux ETF mondiaux.

### 3.4 Devises
- **Devise de référence** : euro (EUR) pour la valeur consolidée.
- **Affichage par action** : devise native de la place de cotation.
- Conversion automatique aux taux de change du jour pour la consolidation.

### 3.5 Fraîcheur des données
- **Cours de bourse** : cours de clôture J-1.
- **Données financières fondamentales** (ROE, dette, FCF…) : mise à jour automatique à chaque publication trimestrielle de résultats.
- **Taux de change** : mise à jour quotidienne.

---

## 4. Gestion du portefeuille

### 4.1 Structure
Un seul portefeuille par utilisateur. Pas de gestion multi-comptes (PEA / CTO / assurance-vie) à ce stade.

### 4.2 Saisie des positions et transactions

**Saisie manuelle** — pour chaque transaction :
- Type d'opération (achat ou vente).
- Ticker / nom de l'action ou ETF.
- Place de cotation (auto-détectée si possible).
- Quantité.
- Prix unitaire.
- Devise (auto-détectée).
- Date de la transaction.

**Import CSV** :
- Import depuis un courtier.
- Mapping configurable des colonnes.
- Prévisualisation avant validation.
- Détection des doublons.

### 4.3 Historique des transactions
- Toutes les transactions conservées et consultables.
- Tri et filtrage par date, ticker, type.
- Modification ou suppression possible d'une transaction saisie par erreur.

### 4.4 Calcul des positions
À partir de l'historique, l'application calcule automatiquement : quantité détenue, prix de revient moyen pondéré, valeur actuelle, plus/moins-value latente (absolue et %).

---

## 5. Analyse Buffett-style

### 5.1 Critères appliqués

| Critère | Description |
|---|---|
| **Marge de sécurité** | Écart entre prix actuel et estimation de valeur intrinsèque (DCF simplifié, modèle de Gordon-Shapiro pour les actions à dividendes). |
| **ROE / ROIC sur 5-10 ans** | Rentabilité des capitaux et stabilité dans le temps. |
| **Ratio dette / capitaux propres** | Santé financière et levier. |
| **Free Cash Flow et croissance** | Capacité à générer du cash réel sur la durée. |
| **Régularité et croissance des dividendes** | Historique de versement et CAGR. |
| **Cercle de compétence** | Tag sectoriel défini par l'utilisateur. Action hors cercle = signalement. |

### 5.2 Cercle de compétence
- L'utilisateur définit dans son profil les secteurs qu'il déclare comprendre.
- Les actions hors cercle reçoivent un avertissement visuel.
- Le cercle de compétence influence le score global (pondération paramétrable).

### 5.3 Restitution
Pour chaque action :
- **Score global synthétique** (0-100).
- **Détail par critère** : score individuel + valeur brute + commentaire interprétatif.
- **Recommandation textuelle** dérivée du score :
  - 80-100 : opportunité forte
  - 60-79 : intéressant
  - 40-59 : à surveiller
  - 0-39 : à éviter / à vendre

### 5.4 Recommandation sur les positions existantes
Pour chaque action détenue :
- Score Buffett actuel.
- Recommandation textuelle : Renforcer / Garder / Alléger / Vendre.
- Raisons principales justifiant la recommandation.

---

## 6. Fonctionnalité centrale : allocation mensuelle

### 6.1 Principe
L'utilisateur saisit un montant. L'application propose une répartition selon une stratégie mixte.

### 6.2 Stratégie de répartition
Combinaison de deux logiques :
- **Renforcement de positions existantes sous-valorisées** (actions détenues avec bon score Buffett actuel).
- **Nouvelles opportunités** (actions non détenues avec score élevé).

La pondération entre les deux est ajustable à chaque allocation (curseur ex : 70% renforcement / 30% nouvelles).

### 6.3 Gestion du nombre d'actions entier
Lorsque le montant ne permet pas d'acheter un nombre entier d'actions selon la répartition idéale, l'application propose **plusieurs répartitions alternatives**, chacune avec :
- Détail des actions et quantités.
- Montant total réellement investi.
- Cash résiduel non investi.
- Score Buffett moyen pondéré de la répartition.

L'utilisateur choisit.

### 6.4 Contraintes de diversification
Deux alertes :
- **Concentration sectorielle** : si un secteur dépasserait un seuil paramétrable (par défaut 30%).
- **Concentration par ligne** : si une action dépasserait un seuil paramétrable (par défaut 10%).

Seuils configurables dans le profil utilisateur.

### 6.5 Validation et saisie des achats
Pas d'étape de simulation préalable obligatoire : l'utilisateur saisit directement les transactions effectivement réalisées chez son courtier. L'écran de saisie post-allocation est pré-rempli avec la répartition choisie pour faciliter la saisie.

---

## 7. Tableau de bord et visualisation

### 7.1 Vue d'ensemble
- **Valeur totale** du portefeuille (EUR) et plus/moins-value globale.
- **Détail par action** : nom, ticker, quantité, PRU, cours actuel, valeur, % du portefeuille, performance.
- **Répartition sectorielle** (graphique).
- **Répartition géographique** (graphique).
- **Historique de la valeur du portefeuille** (courbe temporelle).
- **Suivi des scores Buffett** des actions détenues dans le temps.

### 7.2 Périodes de performance
1 mois / 3 mois / 6 mois / 1 an / YTD / depuis le dernier achat (par action) / depuis l'origine.

### 7.3 Vue détaillée par action
Au clic : caractéristiques (secteur, pays, devise), score Buffett global et détail, recommandation actuelle, historique des transactions sur cette ligne, graphique de cours, évolution du score dans le temps.

---

## 8. Synthèse des écrans

| Écran | Contenu |
|---|---|
| Connexion / Inscription | Auth email/MDP + SSO Google/Apple |
| Tableau de bord | Vue d'ensemble portefeuille |
| Mon portefeuille | Liste détaillée des positions |
| Détail d'une action | Score, recommandation, historique |
| Allocation mensuelle | Saisie montant + propositions de répartition |
| Saisie transaction | Achat/vente manuel ou import CSV |
| Historique | Toutes les transactions |
| Analyse / Watchlist | Exploration de l'univers |
| Profil utilisateur | Cercle de compétence, seuils, préférences |

---

## 9. Règles transverses

- **Notifications** : aucune en V1. L'utilisateur consulte à son rythme.
- **Langue** : français en V1, architecture prête pour multilingue.
- **Données utilisateur** : cloisonnement strict, suppression de compte possible à tout moment.
- **Disponibilité visée** : 99% hors maintenance.
- **Performance** : tableau de bord < 2s en conditions normales.

---

## 10. Points à trancher avant conception détaillée

1. **Fournisseur de données financières** (Financial Modeling Prep, Alpha Vantage, EOD Historical Data, Twelve Data, IEX Cloud…).
2. **Méthode précise de calcul de la valeur intrinsèque** (DCF, multiples, dividend discount model).
3. **Pondération exacte des critères** dans le score Buffett (par défaut : équipondération + bonus/malus cercle de compétence).
4. **Règles précises de l'algorithme d'allocation** (montant minimum par ligne, nombre max de lignes proposées).
5. **Modèle économique** : gratuit, freemium, abonnement ?

---

## 11. Glossaire

| Terme | Définition |
|---|---|
| **Marge de sécurité** | Écart entre prix d'achat et valeur intrinsèque estimée. |
| **ROE** | Return On Equity. Rentabilité des capitaux propres. |
| **ROIC** | Return On Invested Capital. Rentabilité des capitaux investis (fonds propres + dette). |
| **FCF** | Free Cash Flow. Flux de trésorerie disponible après investissements de maintien. |
| **Cercle de compétence** | Ensemble des secteurs qu'un investisseur comprend suffisamment pour évaluer la qualité d'une entreprise. |
| **Long terme** | Dans cette application : horizon supérieur à 5 ans. |

---

Quelques observations PM sur ce que tu as construit, si ça t'intéresse :

Le choix de proposer plusieurs répartitions alternatives plutôt qu'une seule est intelligent — ça respecte ton autonomie de décision tout en automatisant le calcul. C'est plus défendable qu'un faux conseil personnalisé.

La double contrainte de diversification (sectorielle + par ligne) est saine, mais surveille la pondération avec le score Buffett : un bon score peut entrer en conflit avec une contrainte de diversification, et il faut décider qui gagne. À documenter dans la phase de conception.

Le point qui mérite probablement le plus d'attention en V2 : la **valeur intrinsèque**. C'est le cœur de l'approche Buffett et c'est aussi le plus difficile à automatiser proprement. Un DCF simplifié paramétrable est un bon compromis V1, mais prévois une itération.
****