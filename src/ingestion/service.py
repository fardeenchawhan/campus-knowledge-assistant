from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import UserRole
from src.chunks.models import Chunk
from src.documents.models import Document, DocumentVersion
from src.embeddings.service import generate_embeddings
from src.ingestion.chunker import chunk_markdown
from src.ingestion.hash import calculate_file_hash
import asyncio
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

EMBEDDING_BATCH_SIZE = 32


async def ingest_document(
    db: AsyncSession,
    markdown_path: str,
    title: str,
    source: str,
    year: int,
    access_level: str = "student",
    source_hash: str | None = None,
    source_file_name: str | None = None,
    document_key: str | None = None,
) -> DocumentVersion:

    path = Path(markdown_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Markdown file not found: {markdown_path}"
        )


    if access_level not in {
        role.value
        for role in UserRole
    }:
        raise ValueError(
            f"Invalid access level: {access_level}"
        )


    content_hash = (
    source_hash
    if source_hash is not None
    else calculate_file_hash(markdown_path)
    )


    # Find or create the document.
    if not document_key:
        raise ValueError("document_key is required.")

    result = await db.execute(
        select(Document).where(Document.document_key == document_key)
    )

    document = result.scalar_one_or_none()


    if document is None:

        document = Document(
            document_key=document_key,
            title=title,
            source=source,
        )

        db.add(document)

        await db.flush()


    # Check whether this exact version already exists.
    result = await db.execute(
        select(DocumentVersion).where(
            DocumentVersion.document_id == document.id,
            DocumentVersion.content_hash == content_hash,
        )
    )

    existing_version = (
        result.scalar_one_or_none()
    )


    if existing_version is not None:

        return existing_version


    # Determine the next version number.
    result = await db.execute(
        select(
            DocumentVersion.version_number
        )
        .where(
            DocumentVersion.document_id
            == document.id
        )
        .order_by(
            DocumentVersion.version_number.desc()
        )
        .limit(1)
    )

    latest_version = (
        result.scalar_one_or_none()
    )


    next_version = (
        latest_version + 1
        if latest_version is not None
        else 1
    )


    # Mark previous versions as not current.
    await db.execute(
        DocumentVersion.__table__.update()
        .where(
            DocumentVersion.document_id
            == document.id
        )
        .values(is_current=False)
    )


    document_version = DocumentVersion(
        document_id=document.id,
        version_number=next_version,
        file_name=source_file_name or path.name,
        file_path=source,
        extracted_file_path=markdown_path,
        content_hash=content_hash,
        is_current=True,
    )

    db.add(document_version)

    await db.flush()


    # Read extracted Markdown.
    text = path.read_text(
        encoding="utf-8"
    )


    # Create chunks.
    chunks = chunk_markdown(text)


    # Generate embeddings in batches.
    for start in range(
        0,
        len(chunks),
        EMBEDDING_BATCH_SIZE,
    ):

        batch = chunks[
            start:start + EMBEDDING_BATCH_SIZE
        ]

        contents = [
            chunk.content
            for chunk in batch
        ]


        embeddings = await asyncio.to_thread(
            generate_embeddings,
            contents,
        )


        for chunk, embedding in zip(
            batch,
            embeddings,
        ):

            db_chunk = Chunk(
                document_version_id=document_version.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                section=getattr(chunk, "section", None),
                page_number=getattr(chunk, "page_number", None),
                year=year,
                department=None,
                access_level=access_level,
                embedding=embedding,
            )

            db.add(db_chunk)


        await db.flush()


    await db.commit()

    await db.refresh(
        document_version
    )


    logger.info(
        f"Created document version "
        f"{next_version} with "
        f"{len(chunks)} chunks."
    )


    return document_version