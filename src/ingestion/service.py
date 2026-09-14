from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.chunks.models import Chunk
from src.documents.models import Document, DocumentVersion
from src.ingestion.chunker import chunk_markdown


async def ingest_document(
    db: AsyncSession,
    markdown_path: str,
    title: str,
    source: str,
    year: int,
) -> DocumentVersion:
    """
    Create a document, document version, and chunks
    from an extracted Markdown document.
    """

    path = Path(markdown_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Markdown file not found: {markdown_path}"
        )

    # --------------------------------------------------
    # 1. Create the document
    # --------------------------------------------------

    document = Document(
        title=title,
        source=source,
    )

    db.add(document)

    await db.flush()

    # --------------------------------------------------
    # 2. Create the document version
    # --------------------------------------------------

    document_version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        file_name=path.name,
        file_path=str(path),
        content_hash="temporary",
        is_current=True,
    )

    db.add(document_version)

    await db.flush()

    # --------------------------------------------------
    # 3. Read extracted Markdown
    # --------------------------------------------------

    text = path.read_text(
        encoding="utf-8"
    )

    # --------------------------------------------------
    # 4. Create chunks
    # --------------------------------------------------

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

    # --------------------------------------------------
    # 5. Commit everything
    # --------------------------------------------------

    await db.commit()

    await db.refresh(document_version)

    return document_version