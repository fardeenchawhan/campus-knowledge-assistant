from src.chunks.models import Chunk


def build_context(
    chunks: list[Chunk],
) -> tuple[str, list[dict]]:

    context_parts = []
    sources = []

    for index, chunk in enumerate(chunks, start=1):
        print(
        "DEBUG CHUNK:",
        chunk.id,
        "page=",
        chunk.page_number,
        "section=",
        chunk.section,
    )

        document_version = chunk.document_version
        document = document_version.document

        context_parts.append(
            f"[Source {index}]\n"
            f"Document: {document.title}\n"
            f"Version: {document_version.version_number}\n"
            f"Page: {chunk.page_number or 'N/A'}\n"
            f"Section: {chunk.section or 'N/A'}\n"
            f"Chunk ID: {chunk.id}\n"
            f"Content:\n{chunk.content}"
        )

        sources.append(
            {
                "source_number": index,
                "document": document.title,
                "version": document_version.version_number,
                "page": chunk.page_number,
                "section": chunk.section,
                "chunk_id": chunk.id,
            }
        )

    return "\n\n".join(context_parts), sources