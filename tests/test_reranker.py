from unittest.mock import AsyncMock

from src.auth.models import UserRole
from src.retrieval.reranker import reranked_search


def make_chunk(chunk_id: int, content: str):
    return type(
        "FakeChunk",
        (),
        {
            "id": chunk_id,
            "content": content,
        },
    )()


async def test_reranker_sorts_by_reranker_score(monkeypatch):
    chunk_1 = make_chunk(1, "first chunk")
    chunk_2 = make_chunk(2, "second chunk")
    chunk_3 = make_chunk(3, "third chunk")

    monkeypatch.setattr(
        "src.retrieval.reranker.hybrid_search",
        AsyncMock(
            return_value=[
                (chunk_1, 0.5),
                (chunk_2, 0.6),
                (chunk_3, 0.7),
            ]
        ),
    )

    monkeypatch.setattr(
        "src.retrieval.reranker.rerank",
        lambda query, texts: [0.20, 0.95, 0.50],
    )

    results = await reranked_search(
        db=None,
        query="test query",
        role=UserRole.STUDENT,
        top_k=3,
        candidate_k=3,
    )

    returned_ids = [chunk.id for chunk, _ in results]

    assert returned_ids == [2, 3, 1]


async def test_reranker_respects_top_k(monkeypatch):
    chunks = [
        make_chunk(1, "chunk one"),
        make_chunk(2, "chunk two"),
        make_chunk(3, "chunk three"),
    ]

    monkeypatch.setattr(
        "src.retrieval.reranker.hybrid_search",
        AsyncMock(
            return_value=[
                (chunk, 0.5)
                for chunk in chunks
            ]
        ),
    )

    monkeypatch.setattr(
        "src.retrieval.reranker.rerank",
        lambda query, texts: [0.30, 0.90, 0.60],
    )

    results = await reranked_search(
        db=None,
        query="test query",
        role=UserRole.STUDENT,
        top_k=2,
        candidate_k=3,
    )

    assert len(results) == 2
    assert [chunk.id for chunk, _ in results] == [2, 3]