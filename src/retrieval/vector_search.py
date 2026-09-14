from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.chunks.models import Chunk
from src.embeddings.service import generate_embeddings


async def vector_search(
    db: AsyncSession,
    query: str,
    top_k: int = 5,
) -> list[tuple[Chunk, float]]:
    """
    Find the most relevant chunks using
    pgvector cosine similarity.
    """

    # Generate embedding for the user's question
    query_embedding = generate_embeddings([query])[0]

    # Cosine distance
    distance = Chunk.embedding.cosine_distance(
        query_embedding
    )

    statement = (
        select(
            Chunk,
            distance.label("distance"),
        )
        .where(Chunk.embedding.is_not(None))
        .order_by(distance)
        .limit(top_k)
    )

    result = await db.execute(statement)

    rows = result.all()

    return [
        (chunk, 1 - distance_value)
        for chunk, distance_value in rows
    ]