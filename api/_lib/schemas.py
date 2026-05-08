from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, field_validator
import re


# ── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if not re.search(r"\d", v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ── User / Profile ────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProfileResponse(BaseModel):
    competence_circles: list[str]
    sector_threshold: float
    line_threshold: float
    dcf_discount_rate: float
    dcf_terminal_growth_rate: float

    class Config:
        from_attributes = True


class ProfileUpdateRequest(BaseModel):
    competence_circles: Optional[list[str]] = None
    sector_threshold: Optional[float] = None
    line_threshold: Optional[float] = None
    dcf_discount_rate: Optional[float] = None
    dcf_terminal_growth_rate: Optional[float] = None


# ── Instruments ───────────────────────────────────────────────────────────────

class InstrumentResponse(BaseModel):
    ticker: str
    name: str
    sector: Optional[str]
    country: Optional[str]
    currency: Optional[str]
    exchange: Optional[str]
    instrument_type: str

    class Config:
        from_attributes = True


# ── Transactions ──────────────────────────────────────────────────────────────

class TransactionCreateRequest(BaseModel):
    ticker: str
    transaction_type: str  # buy | sell
    quantity: Decimal
    price: Decimal
    currency: str
    transaction_date: date
    exchange: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("transaction_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("buy", "sell"):
            raise ValueError("Le type doit être 'buy' ou 'sell'")
        return v

    @field_validator("quantity", "price")
    @classmethod
    def positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("La valeur doit être positive")
        return v


class TransactionResponse(BaseModel):
    id: str
    ticker: str
    transaction_type: str
    quantity: Decimal
    price: Decimal
    currency: str
    transaction_date: date
    exchange: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Portfolio ─────────────────────────────────────────────────────────────────

class PositionResponse(BaseModel):
    ticker: str
    name: str
    sector: Optional[str]
    country: Optional[str]
    currency: str
    quantity: Decimal
    average_cost: Decimal           # PRU en devise native
    current_price: Decimal          # Cours J-1 en devise native
    current_value_eur: Decimal      # Valeur actuelle en EUR
    cost_basis_eur: Decimal         # Coût total en EUR
    unrealized_pnl_eur: Decimal     # P&L latent en EUR
    unrealized_pnl_pct: float       # P&L latent en %
    portfolio_weight: float         # % du portefeuille total
    buffett_score: Optional[float]
    recommendation: Optional[str]


class PortfolioSummaryResponse(BaseModel):
    total_value_eur: Decimal
    total_cost_eur: Decimal
    total_pnl_eur: Decimal
    total_pnl_pct: float
    positions_count: int
    sector_allocation: dict[str, float]    # {sector: pct}
    country_allocation: dict[str, float]   # {country: pct}


# ── Buffett Score ─────────────────────────────────────────────────────────────

class CriterionDetail(BaseModel):
    score: float
    value: Any
    comment: str


class BuffettScoreResponse(BaseModel):
    ticker: str
    score_date: date
    score_global: float
    score_detail: dict[str, CriterionDetail]
    intrinsic_value: Optional[Decimal]
    safety_margin: Optional[float]
    recommendation: str
    out_of_circle: bool


# ── Allocation ────────────────────────────────────────────────────────────────

class AllocationSimulateRequest(BaseModel):
    amount: Decimal
    reinforcement_ratio: float = 0.7   # 0.0 à 1.0

    @field_validator("reinforcement_ratio")
    @classmethod
    def ratio_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("Le ratio doit être entre 0 et 1")
        return v


class AllocationLine(BaseModel):
    ticker: str
    name: str
    quantity: int
    price_eur: Decimal
    total_eur: Decimal
    buffett_score: float
    is_reinforcement: bool


class AllocationProposal(BaseModel):
    lines: list[AllocationLine]
    total_invested_eur: Decimal
    cash_residual_eur: Decimal
    weighted_score: float
    concentration_alerts: list[str]


class AllocationSimulateResponse(BaseModel):
    proposals: list[AllocationProposal]  # 3 variantes
