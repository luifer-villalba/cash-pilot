"""Add transfer verification fields to transfer_items table.

Revision ID: add_transfer_verification
Revises: a2b3c4d5e6f7
Create Date: 2026-02-16 00:00:00.000000

CP-REPORTS-04: Add transfer verification workflow
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_transfer_verification"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add is_verified, verified_by, and verified_at columns to transfer_items."""
    op.add_column(
        "transfer_items",
        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.create_index(
        "ix_transfer_items_is_verified",
        "transfer_items",
        ["is_verified"],
    )

    op.add_column(
        "transfer_items",
        sa.Column(
            "verified_by",
            sa.UUID(),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_transfer_items_verified_by_users_id",
        "transfer_items",
        "users",
        ["verified_by"],
        ["id"],
    )

    op.add_column(
        "transfer_items",
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove verification columns from transfer_items."""
    op.drop_column("transfer_items", "verified_at")
    op.drop_constraint(
        "fk_transfer_items_verified_by_users_id",
        "transfer_items",
        type_="foreignkey",
    )
    op.drop_column("transfer_items", "verified_by")
    op.drop_index("ix_transfer_items_is_verified", table_name="transfer_items")
    op.drop_column("transfer_items", "is_verified")
