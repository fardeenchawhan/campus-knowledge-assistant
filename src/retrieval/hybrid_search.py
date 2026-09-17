
from sqlalchemy.ext.asyncio import AsyncSession

from src.retrieval.keyword_search import keyword_search
from src.retrieval.vector_search import vector_search
from src.auth.models import UserRole

async def hybrid_search(
    db: AsyncSession,
    query: str,
    role:UserRole,
    top_k: int = 20,
    candidate_k: int = 20,
) -> list[tuple[object, float]]:

    candidates = {}

    # ---------------------------------------------------------
    # Vector search using the ORIGINAL query only
    # ---------------------------------------------------------
    vector_results = await vector_search(
        db=db,
        query=query,
        role=role,
        top_k=candidate_k,
    )

    # ---------------------------------------------------------
    # Keyword search using the ORIGINAL query only
    # ---------------------------------------------------------
    keyword_results = await keyword_search(
        db=db,
        query=query,
        role=role,
        top_k=candidate_k,
    )

    # ---------------------------------------------------------
    # Collect vector candidates
    # ---------------------------------------------------------
    for rank, (chunk, _) in enumerate(vector_results, start=1):
        candidates[chunk.id] = {
            "chunk": chunk,
            "best_vector_rank": rank,
            "best_keyword_rank": None,
        }

    # ---------------------------------------------------------
    # Collect keyword candidates
    # ---------------------------------------------------------
    for rank, (chunk, _) in enumerate(keyword_results, start=1):

        if chunk.id not in candidates:
            candidates[chunk.id] = {
                "chunk": chunk,
                "best_vector_rank": None,
                "best_keyword_rank": rank,
            }

        else:
            candidates[chunk.id]["best_keyword_rank"] = rank



    def candidate_score(item):

        vector_rank = item["best_vector_rank"]
        keyword_rank = item["best_keyword_rank"]

        appears_in_both = (
            vector_rank is not None
            and keyword_rank is not None
        )

        best_rank = min(
            vector_rank if vector_rank is not None else float("inf"),
            keyword_rank if keyword_rank is not None else float("inf"),
        )

        return (
            appears_in_both,
            -best_rank,
        )

    ranked_candidates = sorted(
        candidates.values(),
        key=candidate_score,
        reverse=True,
    )

    return [
        (item["chunk"], 0.0)
        for item in ranked_candidates[:top_k]
    ]