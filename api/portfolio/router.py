from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from api._lib.db import get_db
from api._lib.models import Transaction
from api._lib.schemas import (
    InstrumentResponse,
    PortfolioSummaryResponse,
    PositionResponse,
    TransactionCreateRequest,
    TransactionResponse,
)
from api._lib.security import get_current_user_id
from api._lib.services.market_data import get_provider
from api._lib.services.portfolio import compute_positions, compute_summary, get_or_create_instrument  # noqa: F401

router = APIRouter()


@router.get("/instruments/search", response_model=list[InstrumentResponse])
def search_instruments(q: str = Query(..., min_length=1)):
    provider = get_provider()
    results = provider.search_instruments(q, limit=10)
    return [
        InstrumentResponse(
            ticker=r.ticker,
            name=r.name,
            sector=r.sector,
            country=r.country,
            currency=r.currency,
            exchange=r.exchange,
            instrument_type=r.instrument_type,
        )
        for r in results
    ]


@router.post("/transactions", response_model=TransactionResponse, status_code=201)
def add_transaction(body: TransactionCreateRequest, user_id: str = Depends(get_current_user_id)):
    with get_db() as session:
        instrument = get_or_create_instrument(session, body.ticker)

        tx = Transaction(
            user_id=user_id,
            ticker=instrument.ticker,
            transaction_type=body.transaction_type,
            quantity=body.quantity,
            price=body.price,
            currency=body.currency,
            transaction_date=body.transaction_date,
            exchange=body.exchange,
            notes=body.notes,
        )
        session.add(tx)
        session.flush()
        session.refresh(tx)

        return TransactionResponse(
            id=tx.id,
            ticker=tx.ticker,
            transaction_type=tx.transaction_type,
            quantity=tx.quantity,
            price=tx.price,
            currency=tx.currency,
            transaction_date=tx.transaction_date,
            exchange=tx.exchange,
            notes=tx.notes,
            created_at=tx.created_at or datetime.now(timezone.utc),
        )


@router.get("/transactions", response_model=list[TransactionResponse])
def list_transactions(user_id: str = Depends(get_current_user_id)):
    with get_db() as session:
        txs = session.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.transaction_date.desc())
        ).scalars().all()

        return [
            TransactionResponse(
                id=tx.id,
                ticker=tx.ticker,
                transaction_type=tx.transaction_type,
                quantity=tx.quantity,
                price=tx.price,
                currency=tx.currency,
                transaction_date=tx.transaction_date,
                exchange=tx.exchange,
                notes=tx.notes,
                created_at=tx.created_at or datetime.now(timezone.utc),
            )
            for tx in txs
        ]


@router.delete("/transactions/{tx_id}", status_code=204)
def delete_transaction(tx_id: str, user_id: str = Depends(get_current_user_id)):
    with get_db() as session:
        tx = session.get(Transaction, tx_id)
        if not tx or tx.user_id != user_id:
            raise HTTPException(status_code=404, detail="Transaction introuvable")
        session.delete(tx)


@router.get("/positions", response_model=list[PositionResponse])
def get_positions(user_id: str = Depends(get_current_user_id)):
    with get_db() as session:
        positions, _ = compute_positions(session, user_id)
        return positions


@router.get("/summary", response_model=PortfolioSummaryResponse)
def get_summary(user_id: str = Depends(get_current_user_id)):
    with get_db() as session:
        return compute_summary(session, user_id)
