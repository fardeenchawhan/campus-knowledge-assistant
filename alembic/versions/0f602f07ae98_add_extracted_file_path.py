"""add extracted file path

Revision ID: 0f602f07ae98
Revises: f8e1f1488d00
Create Date: 2026-09-22 13:28:06.713678
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0f602f07ae98"
down_revision: Union[str, Sequence[str], None] = "f8e1f1488d00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_versions",
        sa.Column(
            "extracted_file_path",
            sa.String(length=500),
            nullable=True,
        ),
    )

    # Existing document versions were created before this column existed.
    # Give them an empty value so the column can later become NOT NULL.
    op.execute(
        """
        UPDATE document_versions
        SET extracted_file_path = ''
        WHERE extracted_file_path IS NULL
        """
    )

    op.alter_column(
        "document_versions",
        "extracted_file_path",
        existing_type=sa.String(length=500),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column(
        "document_versions",
        "extracted_file_path",
    )
