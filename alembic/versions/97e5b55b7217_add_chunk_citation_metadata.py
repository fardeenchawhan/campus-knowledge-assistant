from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union

revision = "add_chunk_citation_metadata"
down_revision = "0f602f07ae98"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chunks",
        sa.Column(
            "section",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "chunks",
        sa.Column(
            "page_number",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_chunks_section",
        "chunks",
        ["section"],
    )

    op.create_index(
        "ix_chunks_page_number",
        "chunks",
        ["page_number"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_chunks_page_number",
        table_name="chunks",
    )

    op.drop_index(
        "ix_chunks_section",
        table_name="chunks",
    )

    op.drop_column(
        "chunks",
        "page_number",
    )

    op.drop_column(
        "chunks",
        "section",
    )
