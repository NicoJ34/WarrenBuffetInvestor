"""
Calcul du score Buffett (0-100) et DCF simplifié.
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from api._lib.models import Fundamental
from api._lib.schemas import BuffettScoreResponse, CriterionDetail


# ── Critères individuels ──────────────────────────────────────────────────────

def _score_safety_margin(margin: Optional[float]) -> tuple[float, str]:
    if margin is None:
        return 50.0, "Données insuffisantes pour calculer la marge de sécurité"
    if margin > 30:
        return 100.0, f"Marge de sécurité excellente : +{margin:.1f}%"
    if margin > 15:
        return 70.0, f"Marge de sécurité correcte : +{margin:.1f}%"
    if margin > 0:
        return 40.0, f"Marge de sécurité faible : +{margin:.1f}%"
    return 0.0, f"Action surévaluée — marge négative : {margin:.1f}%"


def _score_roe(roe: Optional[float]) -> tuple[float, str]:
    if roe is None:
        return 50.0, "ROE non disponible"
    if roe > 20:
        return 100.0, f"ROE excellent : {roe:.1f}%"
    if roe > 15:
        return 80.0, f"ROE bon : {roe:.1f}%"
    if roe > 10:
        return 60.0, f"ROE correct : {roe:.1f}%"
    return 20.0, f"ROE insuffisant : {roe:.1f}%"


def _score_debt(de: Optional[float]) -> tuple[float, str]:
    if de is None:
        return 50.0, "Ratio dette/CP non disponible"
    if de < 0.5:
        return 100.0, f"Dette maîtrisée : D/CP = {de:.2f}×"
    if de < 1.0:
        return 70.0, f"Dette modérée : D/CP = {de:.2f}×"
    if de < 2.0:
        return 40.0, f"Dette élevée : D/CP = {de:.2f}×"
    return 10.0, f"Endettement excessif : D/CP = {de:.2f}×"


def _score_fcf(fcf: Optional[float], growth: Optional[float], positive_years: Optional[int]) -> tuple[float, str]:
    if fcf is None:
        return 50.0, "FCF non disponible"
    if fcf <= 0:
        fcf_bn = fcf / 1e9
        return 0.0, f"FCF négatif : {fcf_bn:.1f} Md"
    years = positive_years or 0
    gr = growth or 0
    fcf_bn = fcf / 1e9
    if years >= 4 and gr > 5:
        return 100.0, f"FCF positif {years}/5 ans, croissance {gr:.1f}%/an ({fcf_bn:.1f} Md)"
    if years >= 4:
        return 70.0, f"FCF positif {years}/5 ans, stable ({fcf_bn:.1f} Md)"
    if years >= 2:
        return 30.0, f"FCF irrégulier : {years}/5 ans positif ({fcf_bn:.1f} Md)"
    return 10.0, f"FCF insuffisant : {years}/5 ans positif"


def _score_dividends(div_yield: Optional[float], cagr: Optional[float], years: Optional[int]) -> tuple[float, str]:
    if not div_yield or div_yield == 0:
        return 20.0, "Pas de dividende versé"
    y = years or 0
    gr = cagr or 0
    if y >= 5 and gr > 5:
        return 100.0, f"Dividendes croissants : CAGR {gr:.1f}%/an sur {y} ans (rendement {div_yield:.1f}%)"
    if y >= 5:
        return 60.0, f"Dividendes réguliers sur {y} ans — croissance faible (rendement {div_yield:.1f}%)"
    if y >= 2:
        return 40.0, f"Dividendes récents : {y} ans (rendement {div_yield:.1f}%)"
    return 20.0, "Dividendes irréguliers ou très récents"


def _score_circle(sector: Optional[str], circles: list[str]) -> tuple[float, str]:
    if not sector:
        return 50.0, "Secteur inconnu — impossible d'évaluer le cercle de compétence"
    if not circles:
        return 50.0, "Aucun cercle de compétence défini dans votre profil"
    if sector in circles:
        return 100.0, f"Dans votre cercle de compétence ({sector})"
    return 0.0, f"Hors cercle de compétence ({sector})"


# ── DCF ───────────────────────────────────────────────────────────────────────

def calculate_dcf(
    fcf: Optional[float],
    fcf_growth: Optional[float],
    shares_outstanding: Optional[int],
    current_price: Optional[float],
    discount_rate: float,
    terminal_growth: float,
) -> tuple[Optional[float], Optional[float]]:
    """Retourne (valeur_intrinsèque_par_action, marge_de_sécurité_pct)."""
    if not fcf or fcf <= 0 or not shares_outstanding or shares_outstanding <= 0:
        return None, None

    r = discount_rate
    g = terminal_growth
    if r <= g:
        return None, None

    growth = (fcf_growth / 100) if fcf_growth and fcf_growth > -50 else 0.05

    pv_fcf = 0.0
    fcf_t = float(fcf)
    for t in range(1, 11):
        fcf_t *= (1 + growth)
        pv_fcf += fcf_t / ((1 + r) ** t)

    terminal_value = fcf_t * (1 + g) / (r - g)
    pv_terminal = terminal_value / ((1 + r) ** 10)

    intrinsic_total = pv_fcf + pv_terminal
    intrinsic_per_share = intrinsic_total / shares_outstanding

    safety_margin = None
    if current_price and current_price > 0:
        safety_margin = (intrinsic_per_share - current_price) / intrinsic_per_share * 100

    return intrinsic_per_share, safety_margin


# ── Score global ──────────────────────────────────────────────────────────────

def calculate_buffett_score(
    ticker: str,
    fund: Optional[Fundamental],
    sector: Optional[str],
    current_price: Optional[float],
    competence_circles: list[str],
    discount_rate: float = 0.10,
    terminal_growth: float = 0.03,
) -> BuffettScoreResponse:
    intrinsic, safety_margin = calculate_dcf(
        fcf=fund.fcf if fund else None,
        fcf_growth=fund.fcf_growth_5y if fund else None,
        shares_outstanding=fund.shares_outstanding if fund else None,
        current_price=current_price,
        discount_rate=discount_rate,
        terminal_growth=terminal_growth,
    )

    s_margin, c_margin = _score_safety_margin(safety_margin)
    s_roe, c_roe = _score_roe(fund.roe_5y if fund else None)
    s_debt, c_debt = _score_debt(fund.debt_equity if fund else None)
    s_fcf, c_fcf = _score_fcf(
        fund.fcf if fund else None,
        fund.fcf_growth_5y if fund else None,
        fund.fcf_positive_years if fund else None,
    )
    s_div, c_div = _score_dividends(
        fund.div_yield if fund else None,
        fund.div_cagr_5y if fund else None,
        fund.div_consecutive_years if fund else None,
    )
    s_circle, c_circle = _score_circle(sector, competence_circles)

    score_global = round(
        s_margin * 0.25 + s_roe * 0.20 + s_debt * 0.15 +
        s_fcf * 0.20 + s_div * 0.10 + s_circle * 0.10,
        1,
    )

    if score_global >= 80:
        recommendation = "Renforcer"
    elif score_global >= 60:
        recommendation = "Garder / Renforcer prudemment"
    elif score_global >= 40:
        recommendation = "À surveiller — Garder"
    else:
        recommendation = "À éviter / Vendre"

    out_of_circle = bool(sector and competence_circles and sector not in competence_circles)

    return BuffettScoreResponse(
        ticker=ticker,
        score_date=date.today(),
        score_global=score_global,
        score_detail={
            "marge_securite": CriterionDetail(score=s_margin, value=safety_margin, comment=c_margin),
            "roe": CriterionDetail(score=s_roe, value=fund.roe_5y if fund else None, comment=c_roe),
            "dette": CriterionDetail(score=s_debt, value=fund.debt_equity if fund else None, comment=c_debt),
            "fcf": CriterionDetail(score=s_fcf, value=fund.fcf if fund else None, comment=c_fcf),
            "dividendes": CriterionDetail(score=s_div, value=fund.div_yield if fund else None, comment=c_div),
            "cercle_competence": CriterionDetail(score=s_circle, value=sector, comment=c_circle),
        },
        intrinsic_value=Decimal(str(round(intrinsic, 4))) if intrinsic else None,
        safety_margin=round(safety_margin, 1) if safety_margin is not None else None,
        recommendation=recommendation,
        out_of_circle=out_of_circle,
    )
