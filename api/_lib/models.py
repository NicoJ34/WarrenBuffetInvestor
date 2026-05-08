import uuid
from datetime import date, datetime
from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, Float,
    ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


def _uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # None for SSO-only users
    name = Column(String(255), nullable=False)
    google_id = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    # Circles of competence: list of sector strings
    competence_circles = Column(JSON, nullable=False, default=list)
    # Concentration thresholds (percentages, 0-100)
    sector_threshold = Column(Float, nullable=False, default=30.0)
    line_threshold = Column(Float, nullable=False, default=10.0)
    # DCF parameters
    dcf_discount_rate = Column(Float, nullable=False, default=10.0)
    dcf_terminal_growth_rate = Column(Float, nullable=False, default=3.0)

    user = relationship("User", back_populates="profile")


class Instrument(Base):
    __tablename__ = "instruments"

    ticker = Column(String(20), primary_key=True)
    name = Column(String(255), nullable=False)
    sector = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    currency = Column(String(10), nullable=True)
    exchange = Column(String(50), nullable=True)
    instrument_type = Column(String(20), nullable=False, default="stock")  # stock | etf
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(20), ForeignKey("instruments.ticker"), nullable=False, index=True)
    transaction_type = Column(String(10), nullable=False)  # buy | sell
    quantity = Column(Numeric(18, 6), nullable=False)
    price = Column(Numeric(18, 6), nullable=False)
    currency = Column(String(10), nullable=False)
    transaction_date = Column(Date, nullable=False)
    exchange = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="transactions")
    instrument = relationship("Instrument")


class MarketPrice(Base):
    __tablename__ = "market_prices"
    __table_args__ = (UniqueConstraint("ticker", "price_date"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), ForeignKey("instruments.ticker"), nullable=False, index=True)
    price_date = Column(Date, nullable=False)
    close_price = Column(Numeric(18, 6), nullable=False)
    currency = Column(String(10), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FxRate(Base):
    __tablename__ = "fx_rates"
    __table_args__ = (UniqueConstraint("base_currency", "target_currency", "rate_date"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    base_currency = Column(String(10), nullable=False)
    target_currency = Column(String(10), nullable=False)
    rate_date = Column(Date, nullable=False)
    rate = Column(Numeric(18, 8), nullable=False)


class Fundamental(Base):
    __tablename__ = "fundamentals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), ForeignKey("instruments.ticker"), nullable=False, index=True)
    report_date = Column(Date, nullable=False)
    roe_5y = Column(Float, nullable=True)          # ROE moyen 5 ans (%)
    roic_5y = Column(Float, nullable=True)          # ROIC moyen 5 ans (%)
    debt_equity = Column(Float, nullable=True)      # Ratio dette/capitaux propres
    fcf = Column(Float, nullable=True)              # FCF annuel le plus récent (devise native)
    fcf_growth_5y = Column(Float, nullable=True)    # Croissance FCF CAGR 5 ans (%)
    fcf_positive_years = Column(Integer, nullable=True)  # Nb d'années FCF positif sur 5 ans
    div_yield = Column(Float, nullable=True)        # Rendement dividende actuel (%)
    div_cagr_5y = Column(Float, nullable=True)      # Croissance dividende CAGR 5 ans (%)
    div_consecutive_years = Column(Integer, nullable=True)  # Années consécutives de versement
    shares_outstanding = Column(BigInteger, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("ticker", "report_date"), {"extend_existing": True})


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")


class BuffettScore(Base):
    __tablename__ = "buffett_scores"
    __table_args__ = (UniqueConstraint("ticker", "score_date"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), ForeignKey("instruments.ticker"), nullable=False, index=True)
    score_date = Column(Date, nullable=False)
    score_global = Column(Float, nullable=False)        # 0-100
    score_detail = Column(JSON, nullable=False)         # {criterion: {score, value, comment}}
    intrinsic_value = Column(Numeric(18, 6), nullable=True)  # Valeur intrinsèque par action (devise native)
    safety_margin = Column(Float, nullable=True)        # Marge de sécurité (%)
    recommendation = Column(String(50), nullable=True)  # Renforcer | Garder | Alléger | Vendre
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
