from types import SimpleNamespace

import pytest

from src.ingestion.chunker import chunk_markdown
from src.documents.models import DocumentVersion
from src.ingestion.service import ingest_document


def make_fake_chunks():
    return [
        SimpleNamespace(
            chunk_index=0,
            content="University admission policy.",
            section=None,
            page_number=None,
        ),
        SimpleNamespace(
            chunk_index=1,
            content="Students must submit the required documents.",
            section=None,
            page_number=None,
        ),
    ]


def patch_ingestion_dependencies(monkeypatch):
    monkeypatch.setattr(
        "src.ingestion.service.chunk_markdown",
        lambda text: make_fake_chunks(),
    )

    monkeypatch.setattr(
        "src.ingestion.service.generate_embeddings",
        lambda contents: [
            [1.0, 0.0] + [0.0] * 382
            for _ in contents
        ],
    )


async def test_new_document_creates_version_one(
    db,
    tmp_path,
    monkeypatch,
):
    patch_ingestion_dependencies(monkeypatch)

    markdown_file = tmp_path / "policy.md"
    markdown_file.write_text(
        "# Admission Policy\nStudents must submit documents.",
        encoding="utf-8",
    )

    version = await ingest_document(
        db=db,
        markdown_path=str(markdown_file),
        title="Admission Policy",
        source="policy.pdf",
        year=2026,
        document_key="admission-policy",
        source_hash="hash-v1",
        source_file_name="policy.pdf",
    )

    assert version.version_number == 1
    assert version.is_current is True
    assert version.content_hash == "hash-v1"


async def test_same_content_does_not_create_duplicate_version(
    db,
    tmp_path,
    monkeypatch,
):
    patch_ingestion_dependencies(monkeypatch)

    markdown_file = tmp_path / "policy.md"
    markdown_file.write_text(
        "# Admission Policy\nStudents must submit documents.",
        encoding="utf-8",
    )

    first_version = await ingest_document(
        db=db,
        markdown_path=str(markdown_file),
        title="Admission Policy",
        source="policy.pdf",
        year=2026,
        document_key="admission-policy",
        source_hash="hash-v1",
    )

    second_version = await ingest_document(
        db=db,
        markdown_path=str(markdown_file),
        title="Admission Policy",
        source="policy.pdf",
        year=2026,
        document_key="admission-policy",
        source_hash="hash-v1",
    )

    assert second_version.id == first_version.id
    assert second_version.version_number == 1


async def test_changed_content_creates_new_version(
    db,
    tmp_path,
    monkeypatch,
):
    patch_ingestion_dependencies(monkeypatch)

    markdown_file = tmp_path / "policy.md"
    markdown_file.write_text(
        "# Admission Policy\nUpdated policy.",
        encoding="utf-8",
    )

    first_version = await ingest_document(
        db=db,
        markdown_path=str(markdown_file),
        title="Admission Policy",
        source="policy.pdf",
        year=2026,
        document_key="admission-policy",
        source_hash="hash-v1",
    )

    second_version = await ingest_document(
        db=db,
        markdown_path=str(markdown_file),
        title="Admission Policy",
        source="policy.pdf",
        year=2026,
        document_key="admission-policy",
        source_hash="hash-v2",
    )

    assert first_version.version_number == 1
    assert second_version.version_number == 2
    assert second_version.id != first_version.id
    assert second_version.content_hash == "hash-v2"


async def test_new_version_marks_previous_version_not_current(
    db,
    tmp_path,
    monkeypatch,
):
    patch_ingestion_dependencies(monkeypatch)

    markdown_file = tmp_path / "policy.md"
    markdown_file.write_text(
        "# Admission Policy\nUpdated policy.",
        encoding="utf-8",
    )

    first_version = await ingest_document(
        db=db,
        markdown_path=str(markdown_file),
        title="Admission Policy",
        source="policy.pdf",
        year=2026,
        document_key="admission-policy",
        source_hash="hash-v1",
    )

    second_version = await ingest_document(
        db=db,
        markdown_path=str(markdown_file),
        title="Admission Policy",
        source="policy.pdf",
        year=2026,
        document_key="admission-policy",
        source_hash="hash-v2",
    )

    await db.refresh(first_version)
    await db.refresh(second_version)

    assert first_version.is_current is False
    assert second_version.is_current is True




def test_chunk_markdown_preserves_page_and_section():
    text = """## Eligibility

Students must complete one semester before applying.

<!-- PAGE_BREAK -->

3.4 A minimum academic score of 65 percent is required.
"""

    chunks = chunk_markdown(text)

    assert len(chunks) == 2

    assert chunks[0].page_number == 1
    assert chunks[0].section == "Eligibility"

    assert chunks[1].page_number == 2
    assert chunks[1].section == "3.4"

def test_plain_markdown_has_no_page_number():
    text = """## Eligibility
        Students must complete one semester before applying.
        """

    chunks = chunk_markdown(text)

    assert len(chunks) == 1
    assert chunks[0].page_number is None
    assert chunks[0].section == "Eligibility"