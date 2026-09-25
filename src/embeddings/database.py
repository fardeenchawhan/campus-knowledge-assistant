from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.chunks.models import Chunk
from src.embeddings.service import generate_embeddings
import logging

logger = logging.getLogger(__name__)

async def embed_chunks(
    db: AsyncSession,
    batch_size: int = 32,
) -> int:
    """
    Generate embeddings for chunks that do not
    already have an embedding.
    """

    result = await db.execute(
        select(Chunk)
        .where(Chunk.embedding.is_(None))
        .order_by(Chunk.id)
    )

    chunks = result.scalars().all()

    if not chunks:
        return 0

    total = len(chunks)

    logger.info(f"Generating embeddings for {total} chunks...")

    for start in range(0, total, batch_size):
        batch = chunks[start:start + batch_size]

        texts = [
            chunk.content
            for chunk in batch
        ]

        embeddings = generate_embeddings(texts)

        for chunk, embedding in zip(
            batch,
            embeddings,
        ):
            chunk.embedding = embedding

        await db.commit()


    return total