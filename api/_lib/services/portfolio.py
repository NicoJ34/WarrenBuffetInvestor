from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from api._lib.models import Instrument, Transaction
from api._lib.schemas import PortfolioSummaryResponse, PositionResponse
from api._lib.services.market_data import PriceData, FxRateData, get_provider

_MARKET_TIMEOUT = 8  # seconds per yfinance call


def _safe_price(ticker: str) -> Optional[PriceData]:
    with ThreadPoolExecutor(max_workers=1) as ex:
        try:
            return ex.submit(get_provider().get_price, ticker).result(timeout=_MARKET_TIMEOUT)
        except Exception:
            return None


def _safe_fx(from_ccy: str, to_ccy: str) -> Optional[FxRateData]:
    with ThreadPoolExecutor(max_workers=1) as ex:
        try:
            return ex.submit(get_provider().get_fx_rate, from_ccy, to_ccy).result(timeout=_MARKET_TIMEOUT)
        except Exception:
            return None


def get_or_create_instrument(session: Session, ticker: str) -> Instrument:
    upper = ticker.upper()
    instrument = session.get(Instrument, upper)
    if instrument:
        return instrument

    # Try to enrich via market data — non-blocking if unavailable (rate limit, network)
    provider = get_provider()
    info = provider.get_instrument_info(upper)

    instrument = Instrument(
        ticker=upper,
        name=info.name if info else upper,
        sector=info.sector if info else None,
        country=info.country if info else None,
        currency=info.currency if info else "USD",
        exchange=info.exchange if info else "",
        instrument_type=info.instrument_type if info else "stock",
    )
    session.add(instrument)
    session.flush()
    return instrument


def compute_positions(session: Session, user_id: str) -> tuple[list[PositionResponse], Decimal]:
    transactions = session.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date)
    ).scalars().all()

    by_ticker: dict[str, list[Transaction]] = {}
    for tx in transactions:
        by_ticker.setdefault(tx.ticker, []).append(tx)

    provider = get_provider()
    raw_positions = []
    total_value_eur = Decimal("0")

    for ticker, txs in by_ticker.items():
        buy_qty = Decimal("0")
        buy_total = Decimal("0")
        sell_qty = Decimal("0")

        for tx in txs:
            if tx.transaction_type == "buy":
                buy_qty += tx.quantity
                buy_total += tx.quantity * tx.price
            else:
                sell_qty += tx.quantity

        quantity = buy_qty - sell_qty
        if quantity <= 0:
            continue

        average_cost = buy_total / buy_qty if buy_qty > 0 else Decimal("0")
        currency = txs[0].currency

        price_data = _safe_price(ticker)

        fx_data = _safe_fx(currency, "EUR")
        fx_rate = Decimal(str(fx_data.rate)) if fx_data else Decimal("1")

        cost_basis_eur = quantity * average_cost * fx_rate

        if price_data:
            current_price = Decimal(str(price_data.close_price))
            current_value_eur = quantity * current_price * fx_rate
            unrealized_pnl_eur = current_value_eur - cost_basis_eur
            unrealized_pnl_pct = float(unrealized_pnl_eur / cost_basis_eur * 100) if cost_basis_eur > 0 else 0.0
            total_value_eur += current_value_eur
        else:
            current_price = None
            current_value_eur = None
            unrealized_pnl_eur = None
            unrealized_pnl_pct = None
            # Use cost basis to weight position when price unavailable
            total_value_eur += cost_basis_eur

        instrument = session.get(Instrument, ticker)

        raw_positions.append({
            "ticker": ticker,
            "name": instrument.name if instrument else ticker,
            "sector": instrument.sector if instrument else None,
            "country": instrument.country if instrument else None,
            "currency": currency,
            "quantity": quantity,
            "average_cost": average_cost,
            "current_price": current_price,
            "current_value_eur": current_value_eur,
            "cost_basis_eur": cost_basis_eur,
            "unrealized_pnl_eur": unrealized_pnl_eur,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "portfolio_weight": 0.0,
            "buffett_score": None,
            "recommendation": None,
        })

    for p in raw_positions:
        p["portfolio_weight"] = (
            float(p["current_value_eur"] / total_value_eur * 100) if total_value_eur > 0 else 0.0
        )

    return [PositionResponse(**p) for p in raw_positions], total_value_eur


def compute_summary(session: Session, user_id: str) -> PortfolioSummaryResponse:
    positions, total_value_eur = compute_positions(session, user_id)

    total_cost_eur = sum(p.cost_basis_eur for p in positions)
    total_pnl_eur = total_value_eur - total_cost_eur
    total_pnl_pct = float(total_pnl_eur / total_cost_eur * 100) if total_cost_eur > 0 else 0.0

    sector_allocation: dict[str, float] = {}
    country_allocation: dict[str, float] = {}

    for p in positions:
        if p.sector:
            sector_allocation[p.sector] = sector_allocation.get(p.sector, 0.0) + p.portfolio_weight
        if p.country:
            country_allocation[p.country] = country_allocation.get(p.country, 0.0) + p.portfolio_weight

    return PortfolioSummaryResponse(
        total_value_eur=total_value_eur,
        total_cost_eur=total_cost_eur,
        total_pnl_eur=total_pnl_eur,
        total_pnl_pct=total_pnl_pct,
        positions_count=len(positions),
        sector_allocation=sector_allocation,
        country_allocation=country_allocation,
    )
