from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

model = SentenceTransformer(MODEL_NAME)


def generate_embeddings(
    texts: list[str],
) -> list[list[float]]:
    """
    Generate 384-dimensional embeddings
    for a list of texts.
    """

    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    return embeddings.tolist()