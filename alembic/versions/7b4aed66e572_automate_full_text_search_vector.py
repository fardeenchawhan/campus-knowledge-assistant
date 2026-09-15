"""automate full text search vector

Revision ID: 7b4aed66e572
Revises: 5f5b05a70f77
Create Date: 2026-09-15 22:11:52.932663

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7b4aed66e572'
down_revision: Union[str, Sequence[str], None] = '5f5b05a70f77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION chunks_search_vector_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.search_vector :=
                to_tsvector('english', COALESCE(NEW.content, ''));
            RETURN NEW;
        END;
        $$;
    """)

    op.execute("""
        CREATE TRIGGER chunks_search_vector_trigger
        BEFORE INSERT OR UPDATE OF content
        ON chunks
        FOR EACH ROW
        EXECUTE FUNCTION chunks_search_vector_update();
    """)

    op.execute("""
        UPDATE chunks
        SET search_vector =
            to_tsvector('english', COALESCE(content, ''));
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER IF EXISTS chunks_search_vector_trigger
        ON chunks;
    """)

    op.execute("""
        DROP FUNCTION IF EXISTS chunks_search_vector_update();
    """)
