from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.chunks.models import Chunk


async def keyword_search(
    db: AsyncSession,
    query: str,
    top_k: int = 5,
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
        .where(
            Chunk.search_vector.op("@@")(ts_query)
        )
        .order_by(rank.desc())
        .limit(top_k)
    )

    result = await db.execute(statement)

    return result.all()