from dataclasses import dataclass


@dataclass
class TextChunk:
    """
    Represents one chunk of a document.
    """

    chunk_index: int
    content: str


def chunk_markdown(
    text: str,
    max_characters: int = 1500,
) -> list[TextChunk]:
    """
    Split Markdown into chunks while trying to preserve
    section boundaries.
    """

    sections = text.split("\n## ")

    chunks: list[TextChunk] = []

    chunk_index = 0

    for section in sections:
        section = section.strip()

        if not section:
            continue

        if len(section) <= max_characters:
            chunks.append(
                TextChunk(
                    chunk_index=chunk_index,
                    content=section,
                )
            )

            chunk_index += 1
            continue

        paragraphs = section.split("\n\n")

        current_chunk = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()

            if not paragraph:
                continue

            proposed_chunk = (
                f"{current_chunk}\n\n{paragraph}"
                if current_chunk
                else paragraph
            )

            if len(proposed_chunk) <= max_characters:
                current_chunk = proposed_chunk
            else:
                if current_chunk:
                    chunks.append(
                        TextChunk(
                            chunk_index=chunk_index,
                            content=current_chunk,
                        )
                    )

                    chunk_index += 1

                current_chunk = paragraph

        if current_chunk:
            chunks.append(
                TextChunk(
                    chunk_index=chunk_index,
                    content=current_chunk,
                )
            )

            chunk_index += 1

    return chunks