from unittest.mock import AsyncMock

from src.auth.models import UserRole
from src.retrieval.hybrid_search import hybrid_search


def make_chunk(chunk_id: int):
    return type("FakeChunk", (), {"id": chunk_id})()


async def test_hybrid_prioritizes_chunks_found_in_both_sources(monkeypatch):
    chunk_1 = make_chunk(1)
    chunk_2 = make_chunk(2)
    chunk_3 = make_chunk(3)

    monkeypatch.setattr(
        "src.retrieval.hybrid_search.vector_search",
        AsyncMock(
            return_value=[
                (chunk_1, 0.90),
                (chunk_2, 0.80),
            ]
        ),
    )

    monkeypatch.setattr(
        "src.retrieval.hybrid_search.keyword_search",
        AsyncMock(
            return_value=[
                (chunk_3, 0.95),
                (chunk_1, 0.70),
            ]
        ),
    )

    results = await hybrid_search(
        db=None,
        query="test query",
        role=UserRole.STUDENT,
        top_k=3,
        candidate_k=3,
    )

    returned_ids = [chunk.id for chunk, _ in results]

    # chunk_1 appears in both searches, so it should come first.
    assert returned_ids[0] == 1


async def test_hybrid_removes_duplicate_chunks(monkeypatch):
    chunk_1 = make_chunk(1)
    chunk_2 = make_chunk(2)

    monkeypatch.setattr(
        "src.retrieval.hybrid_search.vector_search",
        AsyncMock(
            return_value=[
                (chunk_1, 0.90),
                (chunk_2, 0.80),
            ]
        ),
    )

    monkeypatch.setattr(
        "src.retrieval.hybrid_search.keyword_search",
        AsyncMock(
            return_value=[
                (chunk_1, 0.95),
            ]
        ),
    )

    results = await hybrid_search(
        db=None,
        query="test query",
        role=UserRole.STUDENT,
        top_k=10,
        candidate_k=10,
    )

    returned_ids = [chunk.id for chunk, _ in results]

    assert returned_ids.count(1) == 1
    assert len(returned_ids) == 2


async def test_hybrid_respects_top_k(monkeypatch):
    chunks = [make_chunk(i) for i in range(1, 6)]

    monkeypatch.setattr(
        "src.retrieval.hybrid_search.vector_search",
        AsyncMock(
            return_value=[
                (chunk, 0.9)
                for chunk in chunks
            ]
        ),
    )

    monkeypatch.setattr(
        "src.retrieval.hybrid_search.keyword_search",
        AsyncMock(return_value=[]),
    )

    results = await hybrid_search(
        db=None,
        query="test query",
        role=UserRole.STUDENT,
        top_k=3,
        candidate_k=5,
    )

    assert len(results) == 3