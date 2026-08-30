"""per-host client-facing server description (YUKU)

Revision ID: yuku0012desc
Revises: yuku0011groups
Create Date: 2026-08-29

The guard is intentional: an interrupted earlier rollout may have added the
nullable column before Alembic recorded the revision. Advancing that database
must not fail or rebuild the hosts table.
"""
import sqlalchemy as sa
from alembic import op


revision = "yuku0012desc"
down_revision = "yuku0011groups"
branch_labels = None
depends_on = None


def _has_column(name: str) -> bool:
    return name in {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("hosts")
    }


def upgrade() -> None:
    if not _has_column("server_description"):
        op.add_column(
            "hosts", sa.Column("server_description", sa.String(length=30), nullable=True)
        )


def downgrade() -> None:
    if _has_column("server_description"):
        op.drop_column("hosts", "server_description")
