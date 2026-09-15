from sentence_transformers import SentenceTransformer, CrossEncoder


EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


embedding_model = SentenceTransformer(
    EMBEDDING_MODEL_NAME
)

reranker_model = CrossEncoder(
    RERANKER_MODEL_NAME
)


def generate_embeddings(
    texts: list[str],
) -> list[list[float]]:

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

    pairs = [
        [query, text]
        for text in texts
    ]

    scores = reranker_model.predict(pairs)

    return scores.tolist()