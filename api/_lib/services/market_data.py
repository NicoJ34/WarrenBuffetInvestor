"""
Couche abstraite pour les données de marché.
Implémentation principale : Twelve Data (API officielle, fiable).
Fallback : yfinance (scraper non-officiel, peut être rate-limité).
Pour swapper : changer get_provider().
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional
import requests


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


# ── Twelve Data ───────────────────────────────────────────────────────────────

class TwelveDataProvider(MarketDataProvider):
    BASE = "https://api.twelvedata.com"

    def __init__(self, api_key: str):
        self._key = api_key

    def _get(self, endpoint: str, params: dict) -> Optional[dict]:
        try:
            params["apikey"] = self._key
            resp = requests.get(f"{self.BASE}{endpoint}", params=params, timeout=10)
            data = resp.json()
            if data.get("status") == "error" or "code" in data:
                return None
            return data
        except Exception:
            return None

    def get_price(self, ticker: str) -> Optional[PriceData]:
        data = self._get("/time_series", {
            "symbol": ticker,
            "interval": "1day",
            "outputsize": 1,
            "format": "JSON",
        })
        if not data:
            return None
        try:
            values = data.get("values", [])
            if not values:
                return None
            latest = values[0]
            meta = data.get("meta", {})
            price_date = date.fromisoformat(latest["datetime"][:10])
            return PriceData(
                ticker=ticker,
                close_price=float(latest["close"]),
                price_date=price_date,
                currency=meta.get("currency", "USD"),
            )
        except Exception:
            return None

    def get_instrument_info(self, ticker: str) -> Optional[InstrumentInfo]:
        data = self._get("/stocks", {"symbol": ticker, "format": "JSON"})
        if not data:
            return None
        try:
            items = data.get("data", [])
            if not items:
                return None
            item = items[0]
            instrument_type = "etf" if item.get("type", "").lower() in ("etf", "fund") else "stock"
            return InstrumentInfo(
                ticker=item.get("symbol", ticker).upper(),
                name=item.get("name", ticker),
                sector=None,  # Twelve Data basic endpoint ne retourne pas le secteur
                country=item.get("country"),
                currency=item.get("currency", "USD"),
                exchange=item.get("exchange", ""),
                instrument_type=instrument_type,
            )
        except Exception:
            return None

    def get_fx_rate(self, from_currency: str, to_currency: str) -> Optional[FxRateData]:
        if from_currency == to_currency:
            return FxRateData(from_currency, to_currency, 1.0, date.today())
        data = self._get("/exchange_rate", {
            "symbol": f"{from_currency}/{to_currency}",
            "format": "JSON",
        })
        if not data:
            return None
        try:
            return FxRateData(
                base_currency=from_currency,
                target_currency=to_currency,
                rate=float(data["rate"]),
                rate_date=date.today(),
            )
        except Exception:
            return None

    def search_instruments(self, query: str, limit: int = 10) -> list[InstrumentInfo]:
        data = self._get("/symbol_search", {"symbol": query, "outputsize": limit})
        if not data:
            return []
        try:
            results = []
            for item in data.get("data", [])[:limit]:
                instrument_type = "etf" if item.get("instrument_type", "").lower() in ("etf", "fund") else "stock"
                results.append(InstrumentInfo(
                    ticker=item.get("symbol", "").upper(),
                    name=item.get("instrument_name", item.get("symbol", "")),
                    sector=None,
                    country=item.get("country"),
                    currency=item.get("currency", "USD"),
                    exchange=item.get("exchange", ""),
                    instrument_type=instrument_type,
                ))
            return results
        except Exception:
            return []


# ── yfinance (fallback) ───────────────────────────────────────────────────────

class YFinanceProvider(MarketDataProvider):
    def get_price(self, ticker: str) -> Optional[PriceData]:
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if hist.empty:
                return None
            info = t.fast_info
            return PriceData(
                ticker=ticker,
                close_price=float(hist["Close"].iloc[-1]),
                price_date=hist.index[-1].date(),
                currency=getattr(info, "currency", "USD") or "USD",
            )
        except Exception:
            return None

    def get_instrument_info(self, ticker: str) -> Optional[InstrumentInfo]:
        try:
            import yfinance as yf
            upper = ticker.upper()
            t = yf.Ticker(upper)

            try:
                fi = t.fast_info
                currency = getattr(fi, "currency", None) or "USD"
                exchange = getattr(fi, "exchange", None) or ""
            except Exception:
                currency, exchange = "USD", ""

            try:
                hist = t.history(period="5d")
                if hist.empty:
                    return None
            except Exception:
                return None

            name, sector, country, instrument_type = upper, None, None, "stock"
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
                ticker=upper, name=name, sector=sector, country=country,
                currency=currency, exchange=exchange, instrument_type=instrument_type,
            )
        except Exception:
            return None

    def get_fx_rate(self, from_currency: str, to_currency: str) -> Optional[FxRateData]:
        if from_currency == to_currency:
            return FxRateData(from_currency, to_currency, 1.0, date.today())
        try:
            import yfinance as yf
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
        try:
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


# ── Factory ───────────────────────────────────────────────────────────────────

_provider: Optional[MarketDataProvider] = None


def get_provider() -> MarketDataProvider:
    global _provider
    if _provider is None:
        from api._lib.config import get_settings
        key = get_settings().twelve_data_api_key
        if key:
            _provider = TwelveDataProvider(key)
        else:
            _provider = YFinanceProvider()
    return _provider
