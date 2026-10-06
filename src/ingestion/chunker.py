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




def split_chunk_by_token_limit(
    chunk: TextChunk,
    tokenize,
    max_tokens: int = 508,
) -> list[TextChunk]:

    def token_count(text: str) -> int:
        return len(tokenize(text))

    if token_count(chunk.content) <= max_tokens:
        return [chunk]

    words = chunk.content.split()

    pieces: list[str] = []
    current_words: list[str] = []

    for word in words:
        candidate = (
            f"{' '.join(current_words)} {word}"
            if current_words
            else word
        )

        if token_count(candidate) <= max_tokens:
            current_words.append(word)
            continue

        # Save the current valid piece.
        if current_words:
            pieces.append(" ".join(current_words))
            current_words = []

        # Check whether this individual word is itself too large.
        if token_count(word) <= max_tokens:
            current_words = [word]
            continue

        # Extremely long token sequence:
        # split it by characters until each piece fits.
        current_piece = ""

        for char in word:
            candidate_piece = current_piece + char

            if token_count(candidate_piece) <= max_tokens:
                current_piece = candidate_piece
            else:
                if current_piece:
                    pieces.append(current_piece)

                current_piece = char

        if current_piece:
            current_words = [current_piece]

    if current_words:
        pieces.append(" ".join(current_words))

    result = [
        TextChunk(
            chunk_index=chunk.chunk_index,
            content=piece,
            section=chunk.section,
            page_number=chunk.page_number,
        )
        for piece in pieces
    ]

    # Final safety check.
    for piece in result:
        count = token_count(piece.content)
        if count > max_tokens:
            raise ValueError(
                f"Token limit violation: "
                f"{count} tokens > {max_tokens} "
                f"for chunk {piece.chunk_index}"
            )

    return result




def ensure_token_limit(
    chunks: list[TextChunk],
    tokenize,
    max_tokens: int = 508,
) -> list[TextChunk]:

    safe_chunks: list[TextChunk] = []

    for chunk in chunks:
        safe_chunks.extend(
            split_chunk_by_token_limit(
                chunk,
                tokenize,
                max_tokens,
            )
        )

    for index, chunk in enumerate(safe_chunks):
        chunk.chunk_index = index

    return safe_chunks