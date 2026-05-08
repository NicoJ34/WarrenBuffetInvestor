"""initial_schema

Revision ID: 369c3389c672
Revises: 
Create Date: 2026-05-08 17:07:04.746851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '369c3389c672'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("google_id", sa.String(255), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("competence_circles", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("sector_threshold", sa.Float, nullable=False, server_default="30.0"),
        sa.Column("line_threshold", sa.Float, nullable=False, server_default="10.0"),
        sa.Column("dcf_discount_rate", sa.Float, nullable=False, server_default="10.0"),
        sa.Column("dcf_terminal_growth_rate", sa.Float, nullable=False, server_default="3.0"),
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token", "password_reset_tokens", ["token"])

    op.create_table(
        "instruments",
        sa.Column("ticker", sa.String(20), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("exchange", sa.String(50), nullable=True),
        sa.Column("instrument_type", sa.String(20), nullable=False, server_default="stock"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticker", sa.String(20), sa.ForeignKey("instruments.ticker"), nullable=False),
        sa.Column("transaction_type", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("price", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("transaction_date", sa.Date, nullable=False),
        sa.Column("exchange", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_ticker", "transactions", ["ticker"])

    op.create_table(
        "market_prices",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(20), sa.ForeignKey("instruments.ticker"), nullable=False),
        sa.Column("price_date", sa.Date, nullable=False),
        sa.Column("close_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("ticker", "price_date"),
    )
    op.create_index("ix_market_prices_ticker", "market_prices", ["ticker"])

    op.create_table(
        "fx_rates",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("base_currency", sa.String(10), nullable=False),
        sa.Column("target_currency", sa.String(10), nullable=False),
        sa.Column("rate_date", sa.Date, nullable=False),
        sa.Column("rate", sa.Numeric(18, 8), nullable=False),
        sa.UniqueConstraint("base_currency", "target_currency", "rate_date"),
    )

    op.create_table(
        "fundamentals",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(20), sa.ForeignKey("instruments.ticker"), nullable=False),
        sa.Column("report_date", sa.Date, nullable=False),
        sa.Column("roe_5y", sa.Float, nullable=True),
        sa.Column("roic_5y", sa.Float, nullable=True),
        sa.Column("debt_equity", sa.Float, nullable=True),
        sa.Column("fcf", sa.Float, nullable=True),
        sa.Column("fcf_growth_5y", sa.Float, nullable=True),
        sa.Column("fcf_positive_years", sa.Integer, nullable=True),
        sa.Column("div_yield", sa.Float, nullable=True),
        sa.Column("div_cagr_5y", sa.Float, nullable=True),
        sa.Column("div_consecutive_years", sa.Integer, nullable=True),
        sa.Column("shares_outstanding", sa.BigInteger, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("ticker", "report_date"),
    )
    op.create_index("ix_fundamentals_ticker", "fundamentals", ["ticker"])

    op.create_table(
        "buffett_scores",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(20), sa.ForeignKey("instruments.ticker"), nullable=False),
        sa.Column("score_date", sa.Date, nullable=False),
        sa.Column("score_global", sa.Float, nullable=False),
        sa.Column("score_detail", sa.JSON, nullable=False),
        sa.Column("intrinsic_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("safety_margin", sa.Float, nullable=True),
        sa.Column("recommendation", sa.String(50), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("ticker", "score_date"),
    )
    op.create_index("ix_buffett_scores_ticker", "buffett_scores", ["ticker"])


def downgrade() -> None:
    op.drop_table("buffett_scores")
    op.drop_table("fundamentals")
    op.drop_table("fx_rates")
    op.drop_table("market_prices")
    op.drop_table("transactions")
    op.drop_table("instruments")
    op.drop_table("password_reset_tokens")
    op.drop_table("user_profiles")
    op.drop_table("users")
