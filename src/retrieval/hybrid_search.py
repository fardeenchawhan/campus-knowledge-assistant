from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from src.retrieval.vector_search import vector_search
from src.retrieval.keyword_search import keyword_search


async def hybrid_search(
    db: AsyncSession,
    query: str,
    top_k: int = 5,
    candidate_k: int = 10,
) -> list[tuple[object, float]]:

    vector_results = await vector_search(
        db=db,
        query=query,
        top_k=candidate_k,
    )

    keyword_results = await keyword_search(
        db=db,
        query=query,
        top_k=candidate_k,
    )

    scores = defaultdict(float)
    chunks = {}

    k = 60

    # Vector results
    for rank, (chunk, _) in enumerate(vector_results, start=1):

        scores[chunk.id] += 1 / (k + rank)
        chunks[chunk.id] = chunk

    # Keyword results
    for rank, (chunk, _) in enumerate(keyword_results, start=1):

        scores[chunk.id] += 1 / (k + rank)
        chunks[chunk.id] = chunk

    ranked_results = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    return [
        (chunks[chunk_id], score)
        for chunk_id, score in ranked_results[:top_k]
    ]