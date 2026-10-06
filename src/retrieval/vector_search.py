from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import settings
from src.chunks.models import Chunk
from src.documents.models import DocumentVersion
from src.embeddings.service import generate_embeddings
from src.auth.rbac import get_allowed_access_levels
from src.auth.models import UserRole


def _generate_query_embedding(query: str) -> list[float]:
    if settings.INFERENCE_MODE == "remote":
        from src.embeddings.remote import generate_embeddings as remote_embed

        return remote_embed(
            [query],
            input_type="search_query",
        )[0]

    return generate_embeddings([query])[0]

async def vector_search(
    db: AsyncSession,
    query: str,
    role:UserRole,
    top_k: int = 20,
) -> list[tuple[Chunk, float]]:

    query_embedding = _generate_query_embedding(query)

    allowed_access_levels = get_allowed_access_levels(role)

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
             Chunk.access_level.in_(allowed_access_levels),
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