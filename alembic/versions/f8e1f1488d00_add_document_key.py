"""add document key

Revision ID: f8e1f1488d00
Revises: 06748966755e
Create Date: 2026-09-20 22:51:07.050710

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8e1f1488d00'
down_revision: Union[str, Sequence[str], None] = '06748966755e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # 1. Add the column temporarily as nullable
    op.add_column(
        "documents",
        sa.Column("document_key", sa.String(length=150), nullable=True),
    )

    # 2. Give existing documents a unique legacy key
    op.execute(
        """
        UPDATE documents
        SET document_key = 'legacy-' || id
        WHERE document_key IS NULL
        """
    )

    # 3. Make the column required
    op.alter_column(
        "documents",
        "document_key",
        existing_type=sa.String(length=150),
        nullable=False,
    )

    # 4. Make document_key unique
    op.create_unique_constraint(
        "uq_documents_document_key",
        "documents",
        ["document_key"],
    )

    # 5. Add index for fast lookup
    op.create_index(
        "ix_documents_document_key",
        "documents",
        ["document_key"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "ix_documents_document_key",
        table_name="documents",
    )

    op.drop_constraint(
        "uq_documents_document_key",
        "documents",
        type_="unique",
    )

    op.drop_column("documents", "document_key")
