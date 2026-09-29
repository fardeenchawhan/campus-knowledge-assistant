from types import SimpleNamespace
from unittest.mock import AsyncMock

from httpx import AsyncClient

from src.auth.models import User, UserRole
from src.auth.security import hash_password

from src.rag.service import UNKNOWN_ANSWER


async def create_user(
    db,
    *,
    name: str,
    email: str,
    password: str,
    role: UserRole,
):
    user = User(
        name=name,
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def login(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]




def make_fake_chunk(
    *,
    chunk_id: int = 1,
    content: str = "...",
    document_title: str = "...",
    version_number: int = 1,
    page_number: int | None = 1,
    section: str | None = "Test Section",
):
    document = SimpleNamespace(
        title=document_title,
    )

    document_version = SimpleNamespace(
        version_number=version_number,
        document=document,
    )

    chunk = SimpleNamespace(
        id=chunk_id,
        content=content,
        section=section,
        page_number=page_number,
        document_version=document_version,
    )

    return chunk


async def test_rag_requires_authentication(client):
    

    response = await client.post(
        "/rag/ask",
        json={
            "question": "What is the attendance policy?",
        },
    )

    assert response.status_code == 401


async def test_rag_returns_unknown_when_no_chunks(
    client,
    db,
    monkeypatch,
):
    

    monkeypatch.setattr(
        "src.rag.service.reranked_search",
        AsyncMock(return_value=[]),
    )

    user = await create_user(
        db,
        name="Student",
        email="student-rag@example.com",
        password="password123",
        role=UserRole.STUDENT,
    )

    token = await login(
        client,
        "student-rag@example.com",
        "password123",
    )

    response = await client.post(
        "/rag/ask",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "question": "What is the attendance policy?",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["answer"] == UNKNOWN_ANSWER
    assert data["sources"] == []


async def test_rag_returns_answer(
    client,
    db,
    monkeypatch,
):
    

    fake_chunk = make_fake_chunk(
        chunk_id=1,
        content="Students must maintain 75% attendance.",
        document_title="Attendance Policy",
        version_number=1,
    )

    monkeypatch.setattr(
        "src.rag.service.reranked_search",
        AsyncMock(
            return_value=[
                (fake_chunk, 0.95),
            ]
        ),
    )

    monkeypatch.setattr(
        "src.rag.service.generate_answer",
        AsyncMock(
            return_value=(
                "Students must maintain 75% attendance. "
                "[Source 1]"
            )
        ),
    )

    await create_user(
        db,
        name="Student",
        email="student-answer@example.com",
        password="password123",
        role=UserRole.STUDENT,
    )

    token = await login(
        client,
        "student-answer@example.com",
        "password123",
    )

    response = await client.post(
        "/rag/ask",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "question": "What is the attendance requirement?",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["answer"] == (
        "Students must maintain 75% attendance. [Source 1]"
    )

    assert data["sources"] == [
        {
            "source_number": 1,
            "document": "Attendance Policy",
            "version": 1,
            "page":1,
            "section":"Test Section",
            "chunk_id": 1,
        }
    ]


async def test_invalid_citation_is_removed(
    client,
    db,
    monkeypatch,
):
    

    fake_chunk = make_fake_chunk(
        chunk_id=10,
        content="The scholarship requires a minimum GPA of 7.5.",
        document_title="Scholarship Policy",
        version_number=2,
    )

    monkeypatch.setattr(
        "src.rag.service.reranked_search",
        AsyncMock(
            return_value=[
                (fake_chunk, 0.90),
            ]
        ),
    )

    monkeypatch.setattr(
        "src.rag.service.generate_answer",
        AsyncMock(
            return_value=(
                "The minimum GPA is 7.5. "
                "[Source 1] "
                "[Source 99]"
            )
        ),
    )

    await create_user(
        db,
        name="Student",
        email="student-citation@example.com",
        password="password123",
        role=UserRole.STUDENT,
    )

    token = await login(
        client,
        "student-citation@example.com",
        "password123",
    )

    response = await client.post(
        "/rag/ask",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "question": "What is the scholarship GPA requirement?",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["answer"] == (
        "The minimum GPA is 7.5. [Source 1]"
    )

    assert "Source 99" not in data["answer"]

    assert data["sources"] == [
        {
            "source_number": 1,
            "document": "Scholarship Policy",
            "version": 2,
            "page":1,
            "section":"Test Section",
            "chunk_id": 10,
        }
    ]


async def test_rag_cache(
    client,
    db,
    monkeypatch,
):
    

    fake_chunk = make_fake_chunk(
        chunk_id=20,
        content="The exam starts at 10 AM.",
        document_title="Exam Schedule",
        version_number=1,
    )

    mock_search = AsyncMock(
        return_value=[
            (fake_chunk, 0.95),
        ]
    )

    mock_generate = AsyncMock(
        return_value="The exam starts at 10 AM. [Source 1]"
    )

    monkeypatch.setattr(
        "src.rag.service.reranked_search",
        mock_search,
    )

    monkeypatch.setattr(
        "src.rag.service.generate_answer",
        mock_generate,
    )

    await create_user(
        db,
        name="Student",
        email="student-cache@example.com",
        password="password123",
        role=UserRole.STUDENT,
    )

    token = await login(
        client,
        "student-cache@example.com",
        "password123",
    )

    question = "When does the exam start?"

    first_response = await client.post(
        "/rag/ask",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "question": question,
        },
    )

    second_response = await client.post(
        "/rag/ask",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "question": question,
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    assert first_response.json() == second_response.json()

    assert mock_search.await_count == 1
    assert mock_generate.await_count == 1


async def test_rag_cache_is_separated_by_role(
    client,
    db,
    monkeypatch,
):
    

    fake_chunk = make_fake_chunk(
        chunk_id=30,
        content="Professors have access to faculty examination guidelines.",
        document_title="Faculty Policy",
        version_number=1,
    )

    mock_search = AsyncMock(
        return_value=[
            (fake_chunk, 0.95),
        ]
    )

    mock_generate = AsyncMock(
        return_value="Professors have access to faculty examination guidelines. [Source 1]"
    )

    monkeypatch.setattr(
        "src.rag.service.reranked_search",
        mock_search,
    )

    monkeypatch.setattr(
        "src.rag.service.generate_answer",
        mock_generate,
    )

    await create_user(
        db,
        name="Student",
        email="cache-student@example.com",
        password="password123",
        role=UserRole.STUDENT,
    )

    await create_user(
        db,
        name="Professor",
        email="cache-professor@example.com",
        password="password123",
        role=UserRole.PROFESSOR,
    )

    student_token = await login(
        client,
        "cache-student@example.com",
        "password123",
    )

    professor_token = await login(
        client,
        "cache-professor@example.com",
        "password123",
    )

    question = "Who has access to faculty examination guidelines?"

    student_response = await client.post(
        "/rag/ask",
        headers={
            "Authorization": f"Bearer {student_token}",
        },
        json={
            "question": question,
        },
    )

    professor_response = await client.post(
        "/rag/ask",
        headers={
            "Authorization": f"Bearer {professor_token}",
        },
        json={
            "question": question,
        },
    )

    assert student_response.status_code == 200
    assert professor_response.status_code == 200

    # Different roles must create different cache entries.
    assert mock_search.await_count == 2
    assert mock_generate.await_count == 2



