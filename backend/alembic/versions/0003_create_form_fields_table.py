"""create_form_fields_table

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-06

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "form_fields",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("field_type", sa.String(length=20), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("options_json", sa.Text(), nullable=False, server_default="[]"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_form_fields_job_id", "form_fields", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_form_fields_job_id", table_name="form_fields")
    op.drop_table("form_fields")
