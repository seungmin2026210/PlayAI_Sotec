"""init: quotes, quote_items, number_sequences, retired_numbers

Revision ID: 0001_init
Revises:
Create Date: 2026-09-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quotes",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("mgmt_no", sa.String(length=16), nullable=False),
        sa.Column("seq_year", sa.SmallInteger(), nullable=False),
        sa.Column("group_code", sa.String(length=1), nullable=False),
        sa.Column("seq_no", sa.SmallInteger(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("issuer_name", sa.String(length=80), nullable=False),
        sa.Column("customer_name", sa.String(length=200), nullable=False),
        sa.Column("customer_contact_name", sa.String(length=80), nullable=True),
        sa.Column("customer_contact_phone", sa.String(length=40), nullable=True),
        sa.Column("vat_included", sa.Boolean(), nullable=False),
        sa.Column("supply_amount", sa.BigInteger(), nullable=False),
        sa.Column("vat_amount", sa.BigInteger(), nullable=False),
        sa.Column("total_with_vat", sa.BigInteger(), nullable=False),
        sa.Column("items_raw_total", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("purchase_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("mgmt_no", name="uq_quotes_mgmt_no"),
        sa.CheckConstraint("group_code IN ('A','B','C','D','E')", name="ck_quotes_group_code"),
    )
    op.create_index("ix_quotes_group_status", "quotes", ["group_code", "status"])
    op.create_index("ix_quotes_issue_date", "quotes", ["issue_date"])
    op.create_index("ix_quotes_seq", "quotes", ["seq_year", "group_code", "seq_no"])
    op.create_index("ix_quotes_deleted_at", "quotes", ["deleted_at"])

    op.create_table(
        "quote_items",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("quote_id", sa.BigInteger(), nullable=False),
        sa.Column("line_no", sa.SmallInteger(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.BigInteger(), nullable=False),
        sa.Column("line_amount", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="CASCADE"),
        sa.CheckConstraint("qty > 0", name="ck_quote_items_qty_pos"),
        sa.CheckConstraint("unit_price > 0", name="ck_quote_items_price_pos"),
    )
    op.create_index("ix_quote_items_quote_id", "quote_items", ["quote_id"])

    op.create_table(
        "number_sequences",
        sa.Column("seq_year", sa.SmallInteger(), nullable=False),
        sa.Column("group_code", sa.String(length=1), nullable=False),
        sa.Column("last_seq", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("seq_year", "group_code"),
    )

    op.create_table(
        "retired_numbers",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("mgmt_no", sa.String(length=16), nullable=False),
        sa.Column("seq_year", sa.SmallInteger(), nullable=False),
        sa.Column("group_code", sa.String(length=1), nullable=False),
        sa.Column("seq_no", sa.SmallInteger(), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("retired_by", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.String(length=20), nullable=False, server_default="DELETED"),
        sa.UniqueConstraint("mgmt_no", name="uq_retired_numbers_mgmt_no"),
    )


def downgrade() -> None:
    op.drop_table("retired_numbers")
    op.drop_table("number_sequences")
    op.drop_index("ix_quote_items_quote_id", table_name="quote_items")
    op.drop_table("quote_items")
    op.drop_index("ix_quotes_deleted_at", table_name="quotes")
    op.drop_index("ix_quotes_seq", table_name="quotes")
    op.drop_index("ix_quotes_issue_date", table_name="quotes")
    op.drop_index("ix_quotes_group_status", table_name="quotes")
    op.drop_table("quotes")
