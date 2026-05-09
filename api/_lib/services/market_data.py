"""
Couche abstraite pour les données de marché.
Implémentation actuelle : yfinance (gratuit, MVP).
Pour swapper vers FMP ou Twelve Data : implémenter MarketDataProvider et changer get_provider().
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional
import yfinance as yf


@dataclass
class PriceData:
    ticker: str
    close_price: float
    price_date: date
    currency: str


@dataclass
class InstrumentInfo:
    ticker: str
    name: str
    sector: Optional[str]
    country: Optional[str]
    currency: str
    exchange: str
    instrument_type: str  # stock | etf


@dataclass
class FxRateData:
    base_currency: str
    target_currency: str
    rate: float
    rate_date: date


class MarketDataProvider(ABC):
    @abstractmethod
    def get_price(self, ticker: str) -> Optional[PriceData]:
        pass

    @abstractmethod
    def get_instrument_info(self, ticker: str) -> Optional[InstrumentInfo]:
        pass

    @abstractmethod
    def get_fx_rate(self, from_currency: str, to_currency: str) -> Optional[FxRateData]:
        pass

    @abstractmethod
    def search_instruments(self, query: str, limit: int = 10) -> list[InstrumentInfo]:
        pass


class YFinanceProvider(MarketDataProvider):
    def get_price(self, ticker: str) -> Optional[PriceData]:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if hist.empty:
                return None
            last_row = hist.iloc[-1]
            info = t.info
            return PriceData(
                ticker=ticker,
                close_price=float(last_row["Close"]),
                price_date=hist.index[-1].date(),
                currency=info.get("currency", "USD"),
            )
        except Exception:
            return None

    def get_instrument_info(self, ticker: str) -> Optional[InstrumentInfo]:
        upper = ticker.upper()
        t = yf.Ticker(upper)

        # fast_info is lightweight and avoids 429s from the heavy /quoteSummary endpoint
        try:
            fi = t.fast_info
            currency = getattr(fi, "currency", None) or "USD"
            exchange = getattr(fi, "exchange", None) or ""
        except Exception:
            currency = "USD"
            exchange = ""

        # Confirm ticker is real by checking recent price data
        try:
            hist = t.history(period="5d")
            if hist.empty:
                return None
        except Exception:
            return None

        # Try to enrich with full info (may fail due to rate limiting — non-blocking)
        name = upper
        sector = None
        country = None
        instrument_type = "stock"
        try:
            info = t.info
            name = info.get("longName") or info.get("shortName") or upper
            sector = info.get("sector")
            country = info.get("country")
            qt = info.get("quoteType", "EQUITY").lower()
            instrument_type = "etf" if qt == "etf" else "stock"
            currency = info.get("currency", currency)
            exchange = info.get("exchange", exchange)
        except Exception:
            pass

        return InstrumentInfo(
            ticker=upper,
            name=name,
            sector=sector,
            country=country,
            currency=currency,
            exchange=exchange,
            instrument_type=instrument_type,
        )

    def get_fx_rate(self, from_currency: str, to_currency: str) -> Optional[FxRateData]:
        if from_currency == to_currency:
            return FxRateData(from_currency, to_currency, 1.0, date.today())
        try:
            pair = f"{from_currency}{to_currency}=X"
            hist = yf.Ticker(pair).history(period="5d")
            if hist.empty:
                return None
            return FxRateData(
                base_currency=from_currency,
                target_currency=to_currency,
                rate=float(hist["Close"].iloc[-1]),
                rate_date=hist.index[-1].date(),
            )
        except Exception:
            return None

    def search_instruments(self, query: str, limit: int = 10) -> list[InstrumentInfo]:
        # yfinance n'a pas d'endpoint de recherche natif — on tente directement le ticker
        # Une implémentation plus complète utilisera l'API Yahoo Finance search
        try:
            import requests
            url = "https://query2.finance.yahoo.com/v1/finance/search"
            params = {"q": query, "quotesCount": limit, "newsCount": 0}
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            results = []
            for quote in resp.json().get("quotes", []):
                symbol = quote.get("symbol", "")
                if not symbol:
                    continue
                results.append(InstrumentInfo(
                    ticker=symbol,
                    name=quote.get("longname") or quote.get("shortname", symbol),
                    sector=None,
                    country=None,
                    currency=quote.get("currency", "USD"),
                    exchange=quote.get("exchange", ""),
                    instrument_type="etf" if quote.get("quoteType") == "ETF" else "stock",
                ))
            return results
        except Exception:
            return []


_provider: Optional[MarketDataProvider] = None


def get_provider() -> MarketDataProvider:
    global _provider
    if _provider is None:
        _provider = YFinanceProvider()
    return _provider
