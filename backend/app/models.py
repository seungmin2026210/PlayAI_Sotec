"""SQLAlchemy 모델 — TECH 03 데이터 모델과 1:1."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .config import GROUP_CODES
from .database import Base

_GROUP_CHECK = "group_code IN ('" + "','".join(GROUP_CODES) + "')"


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    mgmt_no: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    seq_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    group_code: Mapped[str] = mapped_column(String(1), nullable=False)
    seq_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    issuer_name: Mapped[str] = mapped_column(String(80), nullable=False)

    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_contact_name: Mapped[str | None] = mapped_column(String(80))
    customer_contact_phone: Mapped[str | None] = mapped_column(String(40))

    vat_included: Mapped[bool] = mapped_column(Boolean, nullable=False)

    supply_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    vat_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_with_vat: Mapped[int] = mapped_column(BigInteger, nullable=False)
    items_raw_total: Mapped[int] = mapped_column(BigInteger, nullable=False)

    status: Mapped[str] = mapped_column(String(12), nullable=False)
    reject_reason: Mapped[str | None] = mapped_column(Text)

    purchase_locked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    created_by: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list["QuoteItem"]] = relationship(
        back_populates="quote",
        cascade="all, delete-orphan",
        order_by="QuoteItem.line_no",
    )

    __table_args__ = (
        CheckConstraint(_GROUP_CHECK, name="ck_quotes_group_code"),
        Index("ix_quotes_group_status", "group_code", "status"),
        Index("ix_quotes_issue_date", "issue_date"),
        Index("ix_quotes_seq", "seq_year", "group_code", "seq_no"),
        Index("ix_quotes_deleted_at", "deleted_at"),
    )


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    quote_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False
    )
    line_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    line_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)

    quote: Mapped["Quote"] = relationship(back_populates="items")

    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_quote_items_qty_pos"),
        CheckConstraint("unit_price > 0", name="ck_quote_items_price_pos"),
        Index("ix_quote_items_quote_id", "quote_id"),
    )


class NumberSequence(Base):
    """관리번호 채번용 시퀀스. (seq_year, group_code) 별 독립. TECH 05."""

    __tablename__ = "number_sequences"

    seq_year: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    group_code: Mapped[str] = mapped_column(String(1), primary_key=True)
    last_seq: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")


class RetiredNumber(Base):
    """결번 대장 — 삭제된 관리번호. 재사용 금지 (기획서 6장)."""

    __tablename__ = "retired_numbers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    mgmt_no: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    seq_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    group_code: Mapped[str] = mapped_column(String(1), nullable=False)
    seq_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    retired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    retired_by: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(String(20), nullable=False, server_default="DELETED")

    __table_args__ = (
        UniqueConstraint("mgmt_no", name="uq_retired_numbers_mgmt_no"),
    )
