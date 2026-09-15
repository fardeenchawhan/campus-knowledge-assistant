from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.chunks.models import Chunk
from sqlalchemy.orm import selectinload
from src.documents.models import DocumentVersion

async def keyword_search(
    db: AsyncSession,
    query: str,
    top_k: int = 20,
) -> list[tuple[Chunk, float]]:

    ts_query = func.plainto_tsquery(
        "english",
        query,
    )

    rank = func.ts_rank(
        Chunk.search_vector,
        ts_query,
    )

    statement = (
        select(
            Chunk,
            rank.label("rank"),
        )
        .join(
            DocumentVersion,
            Chunk.document_version_id == DocumentVersion.id,
        )
        .options(
            selectinload(Chunk.document_version)
            .selectinload(DocumentVersion.document)
        )
        .where(
            Chunk.search_vector.op("@@")(ts_query),
            DocumentVersion.is_current.is_(True),
        )
        .order_by(rank.desc())
        .limit(top_k)
    )

    result = await db.execute(statement)

    return result.all()