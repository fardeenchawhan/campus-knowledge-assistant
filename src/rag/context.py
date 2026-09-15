from src.chunks.models import Chunk


def build_context(chunks: list[Chunk]) -> str:
    context_parts = []

    for index, chunk in enumerate(chunks, start=1):
        document_version = chunk.document_version
        document = document_version.document

        context_parts.append(
            f"[Source {index}]\n"
            f"Document: {document.title}\n"
            f"Version: {document_version.version_number}\n"
            f"Chunk ID: {chunk.id}\n"
            f"Content:\n{chunk.content}"
        )

    return "\n\n".join(context_parts)