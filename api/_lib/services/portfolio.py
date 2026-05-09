from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from api._lib.models import FxRate, Instrument, MarketPrice, Transaction
from api._lib.schemas import PortfolioSummaryResponse, PositionResponse
from api._lib.services.market_data import get_provider

_MARKET_TIMEOUT = 8   # seconds per yfinance call
_PRICE_MAX_AGE = 7    # accept cached price up to 7 days old


def _get_price(session: Session, ticker: str) -> Optional[Decimal]:
    """Return latest price from DB cache, refreshing via yfinance if stale/missing."""
    cutoff = date.today() - timedelta(days=_PRICE_MAX_AGE)
    row = session.execute(
        select(MarketPrice)
        .where(MarketPrice.ticker == ticker, MarketPrice.price_date >= cutoff)
        .order_by(MarketPrice.price_date.desc())
    ).scalar_one_or_none()

    if row:
        return Decimal(str(row.close_price))

    # Cache miss — try yfinance
    with ThreadPoolExecutor(max_workers=1) as ex:
        try:
            data = ex.submit(get_provider().get_price, ticker).result(timeout=_MARKET_TIMEOUT)
        except Exception:
            data = None

    if data:
        # Upsert into cache
        existing = session.execute(
            select(MarketPrice).where(
                MarketPrice.ticker == ticker,
                MarketPrice.price_date == data.price_date,
            )
        ).scalar_one_or_none()
        if not existing:
            session.add(MarketPrice(
                ticker=ticker,
                price_date=data.price_date,
                close_price=Decimal(str(data.close_price)),
                currency=data.currency,
            ))
            session.flush()
        return Decimal(str(data.close_price))

    return None


def _get_fx(session: Session, from_ccy: str, to_ccy: str) -> Decimal:
    """Return FX rate from DB cache, refreshing via yfinance if stale/missing."""
    if from_ccy == to_ccy:
        return Decimal("1")

    cutoff = date.today() - timedelta(days=_PRICE_MAX_AGE)
    row = session.execute(
        select(FxRate)
        .where(
            FxRate.base_currency == from_ccy,
            FxRate.target_currency == to_ccy,
            FxRate.rate_date >= cutoff,
        )
        .order_by(FxRate.rate_date.desc())
    ).scalar_one_or_none()

    if row:
        return Decimal(str(row.rate))

    # Cache miss — try yfinance
    with ThreadPoolExecutor(max_workers=1) as ex:
        try:
            data = ex.submit(get_provider().get_fx_rate, from_ccy, to_ccy).result(timeout=_MARKET_TIMEOUT)
        except Exception:
            data = None

    if data:
        existing = session.execute(
            select(FxRate).where(
                FxRate.base_currency == from_ccy,
                FxRate.target_currency == to_ccy,
                FxRate.rate_date == data.rate_date,
            )
        ).scalar_one_or_none()
        if not existing:
            session.add(FxRate(
                base_currency=from_ccy,
                target_currency=to_ccy,
                rate_date=data.rate_date,
                rate=Decimal(str(data.rate)),
            ))
            session.flush()
        return Decimal(str(data.rate))

    return Decimal("1")


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

        current_price = _get_price(session, ticker)
        fx_rate = _get_fx(session, currency, "EUR")

        cost_basis_eur = quantity * average_cost * fx_rate

        if current_price is not None:
            current_value_eur = quantity * current_price * fx_rate
            unrealized_pnl_eur = current_value_eur - cost_basis_eur
            unrealized_pnl_pct = float(unrealized_pnl_eur / cost_basis_eur * 100) if cost_basis_eur > 0 else 0.0
            total_value_eur += current_value_eur
        else:
            current_value_eur = None
            unrealized_pnl_eur = None
            unrealized_pnl_pct = None
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
        val = p["current_value_eur"] if p["current_value_eur"] is not None else p["cost_basis_eur"]
        p["portfolio_weight"] = float(val / total_value_eur * 100) if total_value_eur > 0 else 0.0

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
