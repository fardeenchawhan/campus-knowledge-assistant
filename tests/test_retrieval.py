import pytest

from src.auth.models import UserRole
from src.chunks.models import Chunk
from src.documents.models import Document, DocumentVersion
from src.embeddings.service import generate_embeddings
from src.retrieval.keyword_search import keyword_search
from src.retrieval.vector_search import vector_search


def make_embedding(
    first_value: float = 1.0,
    second_value: float = 0.0,
) -> list[float]:
    return [first_value, second_value] + [0.0] * 382


async def create_document_with_version(
    db,
    *,
    title: str,
    document_key: str,
    version_number: int = 1,
    is_current: bool = True,
):
    document = Document(
        document_key=document_key,
        title=title,
        source="test",
    )

    db.add(document)
    await db.flush()

    version = DocumentVersion(
        document_id=document.id,
        version_number=version_number,
        file_name=f"{document_key}.pdf",
        file_path=f"data/documents/{document_key}.pdf",
        extracted_file_path=f"data/extracted/{document_key}.md",
        content_hash=f"hash-{document_key}-{version_number}",
        is_current=is_current,
    )

    db.add(version)
    await db.flush()

    return document, version


async def create_chunk(
    db,
    *,
    document_version_id: int,
    chunk_index: int,
    content: str,
    access_level: str = "student",
    year: int | None = 2026,
    department: str | None = "CSE",
    embedding: list[float] | None = None,
):
    chunk = Chunk(
        document_version_id=document_version_id,
        chunk_index=chunk_index,
        content=content,
        access_level=access_level,
        year=year,
        department=department,
        embedding=embedding,
    )

    db.add(chunk)
    await db.flush()

    return chunk


@pytest.mark.asyncio
async def test_keyword_search_returns_matching_chunk(db):
    _, version = await create_document_with_version(
        db,
        title="Attendance Policy",
        document_key="attendance-policy",
    )

    matching_chunk = await create_chunk(
        db,
        document_version_id=version.id,
        chunk_index=0,
        content="Students must maintain 75 percent attendance.",
    )

    await create_chunk(
        db,
        document_version_id=version.id,
        chunk_index=1,
        content="Students must submit examination forms on time.",
    )

    await db.commit()

    results = await keyword_search(
        db=db,
        query="attendance",
        role=UserRole.STUDENT,
        top_k=5,
    )

    chunks = [chunk for chunk, _ in results]

    assert matching_chunk.id in [chunk.id for chunk in chunks]


@pytest.mark.asyncio
async def test_keyword_search_respects_top_k(db):
    _, version = await create_document_with_version(
        db,
        title="Attendance Policy",
        document_key="attendance-top-k",
    )

    for index in range(5):
        await create_chunk(
            db,
            document_version_id=version.id,
            chunk_index=index,
            content=f"Attendance requirement number {index}.",
        )

    await db.commit()

    results = await keyword_search(
        db=db,
        query="attendance",
        role=UserRole.STUDENT,
        top_k=2,
    )

    assert len(results) <= 2


@pytest.mark.asyncio
async def test_keyword_search_only_returns_current_versions(db):
    _, old_version = await create_document_with_version(
        db,
        title="Scholarship Policy",
        document_key="scholarship-versioned",
        version_number=1,
        is_current=False,
    )

    _, current_version = await create_document_with_version(
        db,
        title="Scholarship Policy",
        document_key="scholarship-current",
        version_number=2,
        is_current=True,
    )

    old_chunk = await create_chunk(
        db,
        document_version_id=old_version.id,
        chunk_index=0,
        content="Scholarship application requires a minimum GPA.",
    )

    current_chunk = await create_chunk(
        db,
        document_version_id=current_version.id,
        chunk_index=0,
        content="Scholarship application requires a minimum GPA.",
    )

    await db.commit()

    results = await keyword_search(
        db=db,
        query="scholarship GPA",
        role=UserRole.STUDENT,
        top_k=10,
    )

    result_ids = {chunk.id for chunk, _ in results}

    assert current_chunk.id in result_ids
    assert old_chunk.id not in result_ids


@pytest.mark.asyncio
async def test_keyword_search_respects_access_level(db):
    _, version = await create_document_with_version(
        db,
        title="Faculty Policy",
        document_key="faculty-policy",
    )

    student_chunk = await create_chunk(
        db,
        document_version_id=version.id,
        chunk_index=0,
        content="Faculty members must follow the faculty attendance policy.",
        access_level="student",
    )

    professor_chunk = await create_chunk(
        db,
        document_version_id=version.id,
        chunk_index=1,
        content="Faculty members must follow the faculty attendance policy.",
        access_level="professor",
    )

    admin_chunk = await create_chunk(
        db,
        document_version_id=version.id,
        chunk_index=2,
        content="Faculty members must follow the faculty attendance policy.",
        access_level="admin",
    )

    await db.commit()

    student_results = await keyword_search(
        db=db,
        query="faculty attendance policy",
        role=UserRole.STUDENT,
        top_k=10,
    )

    professor_results = await keyword_search(
        db=db,
        query="faculty attendance policy",
        role=UserRole.PROFESSOR,
        top_k=10,
    )

    admin_results = await keyword_search(
        db=db,
        query="faculty attendance policy",
        role=UserRole.ADMIN,
        top_k=10,
    )

    student_ids = {chunk.id for chunk, _ in student_results}
    professor_ids = {chunk.id for chunk, _ in professor_results}
    admin_ids = {chunk.id for chunk, _ in admin_results}

    assert student_chunk.id in student_ids
    assert professor_chunk.id not in student_ids
    assert admin_chunk.id not in student_ids

    assert student_chunk.id in professor_ids
    assert professor_chunk.id in professor_ids
    assert admin_chunk.id not in professor_ids

    assert student_chunk.id in admin_ids
    assert professor_chunk.id in admin_ids
    assert admin_chunk.id in admin_ids


@pytest.mark.asyncio
async def test_keyword_search_returns_empty_for_no_match(db):
    _, version = await create_document_with_version(
        db,
        title="Course Policy",
        document_key="course-policy-no-match",
    )

    await create_chunk(
        db,
        document_version_id=version.id,
        chunk_index=0,
        content="Students must complete the registration process.",
    )

    await db.commit()

    results = await keyword_search(
        db=db,
        query="quantum-mechanics",
        role=UserRole.STUDENT,
        top_k=10,
    )

    assert results == []


@pytest.mark.asyncio
async def test_vector_search_returns_relevant_chunk(db, monkeypatch):
    _, version = await create_document_with_version(
        db,
        title="Attendance Policy",
        document_key="vector-attendance",
    )

    relevant_chunk = await create_chunk(
        db,
        document_version_id=version.id,
        chunk_index=0,
        content="Students must maintain 75 percent attendance.",
        embedding=make_embedding(1.0, 0.0),
    )

    other_chunk = await create_chunk(
        db,
        document_version_id=version.id,
        chunk_index=1,
        content="Students must submit examination forms.",
        embedding=make_embedding(0.0, 1.0),
    )

    await db.commit()

    monkeypatch.setattr(
    "src.retrieval.vector_search.generate_embeddings",
    lambda texts: [make_embedding(1.0, 0.0) for _ in texts],
    )

    results = await vector_search(
        db=db,
        query="attendance requirement",
        role=UserRole.STUDENT,
        top_k=2,
    )

    assert results

    result_ids = [chunk.id for chunk, _ in results]

    assert relevant_chunk.id in result_ids
    assert result_ids.index(relevant_chunk.id) < result_ids.index(other_chunk.id)


@pytest.mark.asyncio
async def test_vector_search_respects_top_k(db, monkeypatch):
    _, version = await create_document_with_version(
        db,
        title="Course Policy",
        document_key="vector-top-k",
    )

    for index in range(5):
        await create_chunk(
            db,
            document_version_id=version.id,
            chunk_index=index,
            content=f"Course requirement {index}.",
            embedding=make_embedding(1.0, 0.0),
        )

    await db.commit()

    monkeypatch.setattr(
    "src.retrieval.vector_search.generate_embeddings",
    lambda texts: [make_embedding(1.0, 0.0) for _ in texts],
    )

    results = await vector_search(
        db=db,
        query="course requirement",
        role=UserRole.STUDENT,
        top_k=2,
    )

    assert len(results) == 2


@pytest.mark.asyncio
async def test_vector_search_only_returns_current_versions(db, monkeypatch):
    _, old_version = await create_document_with_version(
        db,
        title="Course Policy",
        document_key="vector-old",
        version_number=1,
        is_current=False,
    )

    _, current_version = await create_document_with_version(
        db,
        title="Course Policy",
        document_key="vector-current",
        version_number=2,
        is_current=True,
    )

    old_chunk = await create_chunk(
        db,
        document_version_id=old_version.id,
        chunk_index=0,
        content="Course registration requires approval.",
        embedding=make_embedding(1.0, 0.0),
    )

    current_chunk = await create_chunk(
        db,
        document_version_id=current_version.id,
        chunk_index=0,
        content="Course registration requires approval.",
        embedding=make_embedding(1.0, 0.0),
    )

    await db.commit()

    monkeypatch.setattr(
    "src.retrieval.vector_search.generate_embeddings",
    lambda texts: [make_embedding(1.0, 0.0) for _ in texts],
    )

    results = await vector_search(
        db=db,
        query="course registration",
        role=UserRole.STUDENT,
        top_k=10,
    )

    result_ids = {chunk.id for chunk, _ in results}

    assert current_chunk.id in result_ids
    assert old_chunk.id not in result_ids


@pytest.mark.asyncio
async def test_vector_search_respects_access_level(db, monkeypatch):
    _, version = await create_document_with_version(
        db,
        title="Faculty Policy",
        document_key="vector-access",
    )

    student_chunk = await create_chunk(
        db,
        document_version_id=version.id,
        chunk_index=0,
        content="Faculty examination policy.",
        access_level="student",
        embedding=make_embedding(1.0, 0.0),
    )

    professor_chunk = await create_chunk(
        db,
        document_version_id=version.id,
        chunk_index=1,
        content="Faculty examination policy.",
        access_level="professor",
        embedding=make_embedding(1.0, 0.0),
    )

    admin_chunk = await create_chunk(
        db,
        document_version_id=version.id,
        chunk_index=2,
        content="Faculty examination policy.",
        access_level="admin",
        embedding=make_embedding(1.0, 0.0),
    )

    await db.commit()

    monkeypatch.setattr(
    "src.retrieval.vector_search.generate_embeddings",
    lambda texts: [make_embedding(1.0, 0.0) for _ in texts],
    )

    student_results = await vector_search(
        db=db,
        query="faculty examination policy",
        role=UserRole.STUDENT,
        top_k=10,
    )

    professor_results = await vector_search(
        db=db,
        query="faculty examination policy",
        role=UserRole.PROFESSOR,
        top_k=10,
    )

    admin_results = await vector_search(
        db=db,
        query="faculty examination policy",
        role=UserRole.ADMIN,
        top_k=10,
    )

    student_ids = {chunk.id for chunk, _ in student_results}
    professor_ids = {chunk.id for chunk, _ in professor_results}
    admin_ids = {chunk.id for chunk, _ in admin_results}

    assert student_chunk.id in student_ids
    assert professor_chunk.id not in student_ids
    assert admin_chunk.id not in student_ids

    assert student_chunk.id in professor_ids
    assert professor_chunk.id in professor_ids
    assert admin_chunk.id not in professor_ids

    assert student_chunk.id in admin_ids
    assert professor_chunk.id in admin_ids
    assert admin_chunk.id in admin_ids


@pytest.mark.asyncio
async def test_vector_search_returns_empty_when_no_embeddings(
    db,
    monkeypatch,
):
    _, version = await create_document_with_version(
        db,
        title="Course Policy",
        document_key="vector-no-embedding",
    )

    await create_chunk(
        db,
        document_version_id=version.id,
        chunk_index=0,
        content="Course registration information.",
        embedding=None,
    )

    await db.commit()

    monkeypatch.setattr(
    "src.retrieval.vector_search.generate_embeddings",
    lambda texts: [make_embedding(1.0, 0.0) for _ in texts],
    )

    results = await vector_search(
        db=db,
        query="course registration",
        role=UserRole.STUDENT,
        top_k=10,
    )

    assert results == []