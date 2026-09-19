import re
from dataclasses import dataclass


@dataclass
class TextChunk:
    chunk_index: int
    content: str


HEADING_PATTERN = re.compile(r"^##\s+(.+)$")

PROVISION_PATTERN = re.compile(
    r"^(?:-\s*)?(\d+\.\d+)\.?\s+(.*)$"
)


def chunk_markdown(
    text: str,
    max_characters: int = 1500,
) -> list[TextChunk]:

    lines = text.splitlines()

    sections: list[tuple[str, list[str]]] = []

    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Markdown heading
        heading_match = HEADING_PATTERN.match(stripped)

        # Numbered provision such as:
        # 3.4 A minimum of 55%...
        provision_match = PROVISION_PATTERN.match(stripped)

        if heading_match:
            if current_lines:
                sections.append(
                    (current_title, current_lines)
                )

            current_title = heading_match.group(1).strip()
            current_lines = []

        elif provision_match:
            if current_lines:
                sections.append(
                    (current_title, current_lines)
                )

            provision_number = provision_match.group(1)
            provision_text = provision_match.group(2)

            current_title = provision_number
            current_lines = [provision_text]

        else:
            current_lines.append(line)

    if current_lines:
        sections.append(
            (current_title, current_lines)
        )

    chunks: list[TextChunk] = []
    chunk_index = 0

    for title, section_lines in sections:

        paragraphs = re.split(
            r"\n\s*\n",
            "\n".join(section_lines),
        )

        current_chunk = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()

            if not paragraph:
                continue

            title_prefix = (
                f"Section: {title}\n\n"
                if title
                else ""
            )

            proposed_content = (
                f"{current_chunk}\n\n{paragraph}"
                if current_chunk
                else f"{title_prefix}{paragraph}"
            )

            if len(proposed_content) <= max_characters:
                current_chunk = proposed_content

            else:
                if current_chunk:
                    chunks.append(
                        TextChunk(
                            chunk_index=chunk_index,
                            content=current_chunk,
                        )
                    )
                    chunk_index += 1

                if len(paragraph) > max_characters:
                    words = paragraph.split()
                    current_piece = title_prefix

                    for word in words:
                        proposed_piece = (
                            f"{current_piece} {word}"
                            if current_piece.strip()
                            else word
                        )

                        if len(proposed_piece) <= max_characters:
                            current_piece = proposed_piece

                        else:
                            chunks.append(
                                TextChunk(
                                    chunk_index=chunk_index,
                                    content=current_piece.strip(),
                                )
                            )
                            chunk_index += 1

                            current_piece = (
                                f"{title_prefix}{word}"
                            )

                    current_chunk = current_piece.strip()

                else:
                    current_chunk = (
                        f"{title_prefix}{paragraph}"
                    )

        if current_chunk:
            chunks.append(
                TextChunk(
                    chunk_index=chunk_index,
                    content=current_chunk,
                )
            )
            chunk_index += 1

    return chunks