from src.core.config import settings


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate document embeddings.

    The public interface intentionally remains simple so existing
    ingestion code and tests do not need to know which provider is used.
    """
    if settings.INFERENCE_MODE == "remote":
        from src.embeddings.remote import generate_embeddings as remote_embed

        return remote_embed(
            texts,
            input_type="search_document",
        )

    from src.embeddings.local import generate_embeddings as local_embed

    return local_embed(texts)


def generate_query_embedding(query: str) -> list[float]:
    """
    Generate an embedding specifically for a search query.
    """
    if settings.INFERENCE_MODE == "remote":
        from src.embeddings.remote import generate_embeddings as remote_embed

        return remote_embed(
            [query],
            input_type="search_query",
        )[0]

    from src.embeddings.local import generate_embeddings as local_embed

    return local_embed([query])[0]


def rerank(query: str, texts: list[str]) -> list[float]:
    if settings.INFERENCE_MODE == "remote":
        from src.embeddings.remote import rerank as remote_rerank

        return remote_rerank(
            query=query,
            texts=texts,
        )

    from src.embeddings.local import rerank as local_rerank

    return local_rerank(
        query=query,
        texts=texts,
    )