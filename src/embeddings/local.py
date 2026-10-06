from sentence_transformers import SentenceTransformer, CrossEncoder


EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


_embedding_model = None
_reranker_model = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model

    if _embedding_model is None:
        _embedding_model = SentenceTransformer(
            EMBEDDING_MODEL_NAME
        )

    return _embedding_model


def get_reranker_model() -> CrossEncoder:
    global _reranker_model

    if _reranker_model is None:
        _reranker_model = CrossEncoder(
            RERANKER_MODEL_NAME
        )

    return _reranker_model


def generate_embeddings(
    texts: list[str],
) -> list[list[float]]:

    embedding_model = get_embedding_model()

    embeddings = embedding_model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    return embeddings.tolist()


def rerank(
    query: str,
    texts: list[str],
) -> list[float]:

    reranker_model = get_reranker_model()

    pairs = [
        [query, text]
        for text in texts
    ]

    scores = reranker_model.predict(pairs)

    return scores.tolist()