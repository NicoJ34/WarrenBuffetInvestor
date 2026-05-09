"""
Récupération et cache des fondamentaux financiers.
Source principale : Twelve Data. Fallback : yfinance.
Cache 90 jours — mise à jour trimestrielle.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from api._lib.models import Fundamental

_CACHE_DAYS = 90
_FETCH_TIMEOUT = 15


def get_or_fetch_fundamentals(session: Session, ticker: str) -> Optional[Fundamental]:
    cutoff = date.today() - timedelta(days=_CACHE_DAYS)

    fund = session.execute(
        select(Fundamental)
        .where(Fundamental.ticker == ticker, Fundamental.report_date >= cutoff)
        .order_by(Fundamental.report_date.desc())
    ).scalar_one_or_none()

    if fund:
        return fund

    data = _fetch_twelve_data(ticker) or _fetch_yfinance(ticker)

    if data:
        fund = Fundamental(ticker=ticker, report_date=date.today(), **data)
        session.add(fund)
        session.flush()
        return fund

    # Retourne les données périmées si disponibles
    return session.execute(
        select(Fundamental)
        .where(Fundamental.ticker == ticker)
        .order_by(Fundamental.report_date.desc())
    ).scalar_one_or_none()


def _empty_result() -> dict:
    return {
        "roe_5y": None, "roic_5y": None, "debt_equity": None,
        "fcf": None, "fcf_growth_5y": None, "fcf_positive_years": None,
        "div_yield": None, "div_cagr_5y": None, "div_consecutive_years": None,
        "shares_outstanding": None,
    }


def _fetch_twelve_data(ticker: str) -> Optional[dict]:
    """Fetch fundamentals from Twelve Data API."""
    def _fetch():
        from api._lib.config import get_settings
        import requests

        key = get_settings().twelve_data_api_key
        if not key:
            return None

        BASE = "https://api.twelvedata.com"
        result = _empty_result()

        def _get(endpoint: str, params: dict) -> Optional[dict]:
            try:
                params["apikey"] = key
                params["symbol"] = ticker
                resp = requests.get(f"{BASE}{endpoint}", params=params, timeout=10)
                data = resp.json()
                if data.get("status") == "error" or "code" in data:
                    return None
                return data
            except Exception:
                return None

        # --- Statistics (ROE, D/E, shares) ---
        stats = _get("/statistics", {})
        if stats:
            try:
                valuation = stats.get("valuations_metrics", {})
                fin = stats.get("financials", {})
                balance = fin.get("balance_sheet", {})
                income = fin.get("income_statement", {})

                roe = income.get("return_on_equity_ttm")
                if roe is not None:
                    result["roe_5y"] = float(roe) * 100

                de = balance.get("total_debt_to_equity_annual")
                if de is not None:
                    result["debt_equity"] = float(de)

                shares = valuation.get("shares_outstanding")
                if shares is not None:
                    result["shares_outstanding"] = int(float(shares))
            except Exception:
                pass

        # --- Cash Flow (FCF) ---
        cf_data = _get("/cash_flow", {"period": "annual"})
        if cf_data:
            try:
                cf_list = cf_data.get("cash_flow", [])[:5]
                fcf_series = []
                for cf in cf_list:
                    ocf = cf.get("operating_activities")
                    capex = cf.get("capital_expenditures")
                    if ocf is not None and capex is not None:
                        fcf_series.append(float(ocf) + float(capex))

                if fcf_series:
                    result["fcf"] = fcf_series[0]
                    result["fcf_positive_years"] = sum(1 for f in fcf_series if f > 0)
                    if len(fcf_series) >= 2 and fcf_series[-1] > 0 and fcf_series[0] > 0:
                        n = len(fcf_series) - 1
                        result["fcf_growth_5y"] = ((fcf_series[0] / fcf_series[-1]) ** (1 / n) - 1) * 100
            except Exception:
                pass

        # --- Dividends ---
        div_data = _get("/dividends", {"range": "5y", "format": "JSON"})
        if div_data:
            try:
                divs = div_data.get("dividends", [])
                if divs:
                    from collections import defaultdict
                    annual: dict = defaultdict(float)
                    for d in divs:
                        yr = d.get("date", "")[:4]
                        if yr:
                            annual[yr] += float(d.get("amount", 0))

                    yearly = sorted(annual.values())
                    result["div_consecutive_years"] = len(yearly)

                    if len(yearly) >= 2:
                        n = min(len(yearly) - 1, 5)
                        first, last = yearly[0], yearly[-1]
                        if first > 0:
                            result["div_cagr_5y"] = ((last / first) ** (1 / n) - 1) * 100

                # Dividend yield from statistics
                if stats:
                    dy = stats.get("financials", {}).get("income_statement", {}).get("dividend_yield_ttm")
                    if dy is not None:
                        result["div_yield"] = float(dy) * 100
            except Exception:
                pass

        # Return None if we got nothing useful
        if all(v is None for v in result.values()):
            return None
        return result

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(_fetch).result(timeout=_FETCH_TIMEOUT)
    except Exception:
        return None


def _fetch_yfinance(ticker: str) -> Optional[dict]:
    """Fallback : fetch fundamentals from yfinance."""
    def _fetch():
        import yfinance as yf
        result = _empty_result()

        try:
            info = yf.Ticker(ticker).info
            roe = info.get("returnOnEquity")
            if roe is not None:
                result["roe_5y"] = roe * 100
            de = info.get("debtToEquity")
            if de is not None:
                result["debt_equity"] = de / 100
            dy = info.get("dividendYield")
            if dy is not None:
                result["div_yield"] = dy * 100
            result["shares_outstanding"] = info.get("sharesOutstanding")
        except Exception:
            pass

        try:
            cf = yf.Ticker(ticker).cashflow
            if not cf.empty:
                fcf_series = []
                for col in cf.columns[:5]:
                    try:
                        ocf = float(cf.loc["Operating Cash Flow", col]) if "Operating Cash Flow" in cf.index else 0.0
                        capex = float(cf.loc["Capital Expenditure", col]) if "Capital Expenditure" in cf.index else 0.0
                        fcf_series.append(ocf + capex)
                    except Exception:
                        pass
                if fcf_series:
                    result["fcf"] = fcf_series[0]
                    result["fcf_positive_years"] = sum(1 for f in fcf_series if f > 0)
                    if len(fcf_series) >= 2 and fcf_series[-1] > 0 and fcf_series[0] > 0:
                        n = len(fcf_series) - 1
                        result["fcf_growth_5y"] = ((fcf_series[0] / fcf_series[-1]) ** (1 / n) - 1) * 100
        except Exception:
            pass

        try:
            divs = yf.Ticker(ticker).dividends
            if not divs.empty:
                annual = divs.resample("YE").sum()
                annual = annual[annual > 0]
                if len(annual) > 0:
                    result["div_consecutive_years"] = len(annual)
                    if len(annual) >= 2:
                        n = min(len(annual) - 1, 5)
                        first = float(annual.iloc[max(0, len(annual) - n - 1)])
                        last = float(annual.iloc[-1])
                        if first > 0:
                            result["div_cagr_5y"] = ((last / first) ** (1 / n) - 1) * 100
        except Exception:
            pass

        if all(v is None for v in result.values()):
            return None
        return result

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(_fetch).result(timeout=_FETCH_TIMEOUT)
    except Exception:
        return None
