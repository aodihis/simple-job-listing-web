"""add_cv_to_applications

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-07

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("cv_filename", sa.String(255), nullable=True))
    op.add_column("applications", sa.Column("cv_path", sa.String(1000), nullable=True))


def downgrade() -> None:
    op.drop_column("applications", "cv_path")
    op.drop_column("applications", "cv_filename")
