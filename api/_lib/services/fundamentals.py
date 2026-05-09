"""
Récupération et cache des fondamentaux financiers via yfinance.
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

    data = _fetch_from_yfinance(ticker)

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


def _fetch_from_yfinance(ticker: str) -> Optional[dict]:
    def _fetch():
        import yfinance as yf

        t = yf.Ticker(ticker)
        result: dict = {
            "roe_5y": None, "roic_5y": None, "debt_equity": None,
            "fcf": None, "fcf_growth_5y": None, "fcf_positive_years": None,
            "div_yield": None, "div_cagr_5y": None, "div_consecutive_years": None,
            "shares_outstanding": None,
        }

        try:
            info = t.info
            roe = info.get("returnOnEquity")
            if roe is not None:
                result["roe_5y"] = roe * 100

            de = info.get("debtToEquity")
            if de is not None:
                result["debt_equity"] = de / 100  # yfinance retourne en %, on normalise

            dy = info.get("dividendYield")
            if dy is not None:
                result["div_yield"] = dy * 100

            result["shares_outstanding"] = info.get("sharesOutstanding")
        except Exception:
            pass

        try:
            cf = t.cashflow
            if not cf.empty:
                fcf_series = []
                for col in cf.columns[:5]:
                    try:
                        ocf = float(cf.loc["Operating Cash Flow", col]) if "Operating Cash Flow" in cf.index else 0.0
                        capex = float(cf.loc["Capital Expenditure", col]) if "Capital Expenditure" in cf.index else 0.0
                        fcf_series.append(ocf + capex)  # capex est négatif dans yfinance
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
            divs = t.dividends
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

        return result

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(_fetch).result(timeout=_FETCH_TIMEOUT)
    except Exception:
        return None
