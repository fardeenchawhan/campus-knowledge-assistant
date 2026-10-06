from __future__ import annotations

from functools import lru_cache

import cohere

from src.core.config import settings


MAX_EMBED_TOKENS = 508
EMBEDDING_BATCH_SIZE = 96


@lru_cache(maxsize=1)
def get_cohere_client() -> cohere.ClientV2:
    if not settings.COHERE_API_KEY:
        raise RuntimeError(
            "COHERE_API_KEY is required when INFERENCE_MODE=remote."
        )

    return cohere.ClientV2(
        api_key=settings.COHERE_API_KEY
    )


def _validate_mode() -> None:
    if not settings.COHERE_API_KEY:
        raise RuntimeError(
            "COHERE_API_KEY is required when INFERENCE_MODE=remote."
        )


def generate_embeddings(
    texts: list[str],
    *,
    input_type: str = "search_document",
) -> list[list[float]]:

    _validate_mode()

    if not texts:
        return []

    client = get_cohere_client()

    embeddings: list[list[float]] = []

    for start in range(
        0,
        len(texts),
        EMBEDDING_BATCH_SIZE,
    ):
        batch = texts[
            start:start + EMBEDDING_BATCH_SIZE
        ]

        response = client.embed(
            texts=batch,
            model=settings.COHERE_EMBEDDING_MODEL,
            input_type=input_type,
            embedding_types=["float"],
            truncate="NONE",
        )

        embeddings.extend(
            response.embeddings.float
        )

    return embeddings


def rerank(
    query: str,
    texts: list[str],
) -> list[float]:

    _validate_mode()

    if not texts:
        return []

    client = get_cohere_client()

    response = client.rerank(
        model=settings.COHERE_RERANKER_MODEL,
        query=query,
        documents=texts,
        top_n=len(texts),
        max_tokens_per_doc=4096,
    )

    scores = [0.0] * len(texts)

    for result in response.results:
        scores[result.index] = result.relevance_score

    return scores