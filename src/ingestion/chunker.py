import re
from dataclasses import dataclass


@dataclass
class TextChunk:
    chunk_index: int
    content: str
    section: str | None = None
    page_number: int | None = 1


HEADING_PATTERN = re.compile(r"^##\s+(.+)$")

PROVISION_PATTERN = re.compile(
    r"^(?:-\s*)?(\d+\.\d+)\.?\s+(.*)$"
)


PAGE_BREAK_PATTERN = re.compile(
    r"^\s*<!--\s*PAGE_BREAK\s*-->\s*$",
    re.MULTILINE,
)


def chunk_markdown(
    text: str,
    max_characters: int = 1500,
) -> list[TextChunk]:

    lines = text.splitlines()

    sections: list[tuple[str, list[str], int | None]] = []

    current_title = ""
    current_lines: list[str] = []
    has_page_markers = PAGE_BREAK_PATTERN.search(text) is not None
    current_page: int | None = 1 if has_page_markers else None

    def flush_section() -> None:
        nonlocal current_lines

        if current_lines:
            sections.append(
                (
                    current_title,
                    current_lines,
                    current_page,
                )
            )

        current_lines = []

    for line in lines:
        stripped = line.strip()


        if PAGE_BREAK_PATTERN.match(stripped):
            flush_section()

            if current_page is not None:
                current_page += 1

            continue

        heading_match = HEADING_PATTERN.match(stripped)

        provision_match = PROVISION_PATTERN.match(stripped)

        if heading_match:
            flush_section()

            current_title = heading_match.group(1).strip()
            current_lines = []

        elif provision_match:
            flush_section()

            provision_number = provision_match.group(1)
            provision_text = provision_match.group(2)

            current_title = provision_number
            current_lines = [provision_text]

        else:
            current_lines.append(line)

    flush_section()

    chunks: list[TextChunk] = []
    chunk_index = 0

    for title, section_lines, page_number in sections:

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
                            section=title or None,
                            page_number=page_number,
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
                                    section=title or None,
                                    page_number=page_number,
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
                    section=title or None,
                    page_number=page_number,
                )
            )

            chunk_index += 1

    return chunks