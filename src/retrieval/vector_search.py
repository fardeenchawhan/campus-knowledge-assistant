from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.chunks.models import Chunk
from src.documents.models import DocumentVersion
from src.embeddings.service import generate_embeddings


async def vector_search(
    db: AsyncSession,
    query: str,
    top_k: int = 20,
) -> list[tuple[Chunk, float]]:

    query_embedding = generate_embeddings([query])[0]

    distance = Chunk.embedding.cosine_distance(query_embedding)

    statement = (
        select(
            Chunk,
            distance.label("distance"),
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
            Chunk.embedding.is_not(None),
            DocumentVersion.is_current.is_(True),
        )
        .order_by(distance)
        .limit(top_k)
    )

    result = await db.execute(statement)
    rows = result.all()

    return [
        (chunk, 1 - distance_value)
        for chunk, distance_value in rows
    ]