from sqlalchemy.ext.asyncio import AsyncSession

from src.retrieval.hybrid_search import hybrid_search
from src.embeddings.service import rerank


async def reranked_search(
    db: AsyncSession,
    query: str,
    top_k: int = 5,
    candidate_k: int = 10,
):
    candidates = await hybrid_search(
        db=db,
        query=query,
        top_k=candidate_k,
        candidate_k=candidate_k,
    )

    if not candidates:
        return []

    chunks = [
        chunk
        for chunk, _ in candidates
    ]

    texts = [
        chunk.content
        for chunk in chunks
    ]

    reranker_scores = rerank(
        query=query,
        texts=texts,
    )

    reranked = list(
        zip(
            chunks,
            reranker_scores,
        )
    )

    reranked.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    return reranked[:top_k]