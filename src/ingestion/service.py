from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.chunks.models import Chunk
from src.documents.models import Document, DocumentVersion
from src.ingestion.chunker import chunk_markdown
from src.ingestion.hash import calculate_file_hash


async def ingest_document(
    db: AsyncSession,
    markdown_path: str,
    title: str,
    source: str,
    year: int,
) -> DocumentVersion:

    """Ingest a Markdown document with content-based versioning."""

    path = Path(markdown_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Markdown file not found: {markdown_path}"
        )

    # Calculate hash of the source file.
    content_hash = calculate_file_hash(markdown_path)

    # Check whether this document already exists.
    result = await db.execute(
        select(Document)
        .where(Document.title == title)
    )

    document = result.scalar_one_or_none()

    # Create the document if this is the first version.
    if document is None:

        document = Document(
            title=title,
            source=source,
        )

        db.add(document)
        await db.flush()

    # Check whether this exact version already exists.
    result = await db.execute(
        select(DocumentVersion)
        .where(
            DocumentVersion.document_id == document.id,
            DocumentVersion.content_hash == content_hash,
        )
    )

    existing_version = result.scalar_one_or_none()

    if existing_version is not None:
        print(
            f"Document already exists as version "
            f"{existing_version.version_number}."
        )

        return existing_version

    # Get the latest version number.
    result = await db.execute(
        select(DocumentVersion.version_number)
        .where(
            DocumentVersion.document_id == document.id
        )
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    )

    latest_version = result.scalar_one_or_none()

    next_version = (
        latest_version + 1
        if latest_version is not None
        else 1
    )

    # Mark previous versions as no longer current.
    await db.execute(
        DocumentVersion.__table__.update()
        .where(
            DocumentVersion.document_id == document.id
        )
        .values(is_current=False)
    )

    # Create the new version.
    document_version = DocumentVersion(
        document_id=document.id,
        version_number=next_version,
        file_name=path.name,
        file_path=str(path),
        content_hash=content_hash,
        is_current=True,
    )

    db.add(document_version)
    await db.flush()

    # Extract markdown text.
    text = path.read_text(encoding="utf-8")

    # Create chunks.
    chunks = chunk_markdown(text)

    for chunk in chunks:

        db_chunk = Chunk(
            document_version_id=document_version.id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            year=year,
            department=None,
            access_level="student",
        )

        db.add(db_chunk)

    await db.commit()
    await db.refresh(document_version)

    print(
        f"Created document version {next_version} "
        f"with {len(chunks)} chunks."
    )

    return document_version