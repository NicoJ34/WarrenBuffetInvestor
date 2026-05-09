from fastapi import APIRouter, Depends
from sqlalchemy import select

from api._lib.db import get_db
from api._lib.models import Instrument, Transaction, UserProfile
from api._lib.schemas import BuffettScoreResponse
from api._lib.security import get_current_user_id
from api._lib.services.fundamentals import get_or_fetch_fundamentals
from api._lib.services.portfolio import _get_price
from api._lib.services.scoring import calculate_buffett_score

router = APIRouter()


def _get_score_for_ticker(session, ticker: str, user_id: str) -> BuffettScoreResponse:
    instrument = session.get(Instrument, ticker)
    sector = instrument.sector if instrument else None

    profile = session.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).scalar_one_or_none()

    circles = profile.competence_circles if profile else []
    discount_rate = (profile.dcf_discount_rate / 100) if profile else 0.10
    terminal_growth = (profile.dcf_terminal_growth_rate / 100) if profile else 0.03

    current_price = _get_price(session, ticker)
    current_price_f = float(current_price) if current_price else None

    fund = get_or_fetch_fundamentals(session, ticker)

    return calculate_buffett_score(
        ticker=ticker,
        fund=fund,
        sector=sector,
        current_price=current_price_f,
        competence_circles=circles,
        discount_rate=discount_rate,
        terminal_growth=terminal_growth,
    )


@router.get("/{ticker}", response_model=BuffettScoreResponse)
def get_analysis(ticker: str, user_id: str = Depends(get_current_user_id)):
    with get_db() as session:
        return _get_score_for_ticker(session, ticker.upper(), user_id)


@router.get("/portfolio/scores", response_model=list[BuffettScoreResponse])
def get_portfolio_scores(user_id: str = Depends(get_current_user_id)):
    """Retourne les scores Buffett pour toutes les positions du portefeuille."""
    with get_db() as session:
        tickers = session.execute(
            select(Transaction.ticker).where(Transaction.user_id == user_id).distinct()
        ).scalars().all()

        return [_get_score_for_ticker(session, t, user_id) for t in tickers]
