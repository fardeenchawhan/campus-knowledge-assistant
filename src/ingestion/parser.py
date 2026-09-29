from pathlib import Path

from docling.document_converter import DocumentConverter


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".html",
    ".htm",
    ".md",
    ".txt",
}

PAGE_BREAK_MARKER = "<!-- PAGE_BREAK -->"


def validate_file_type(file_path: str) -> None:
    extension = Path(file_path).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))

        raise ValueError(
            f"Unsupported file type: {extension}. "
            f"Supported types: {supported}"
        )


def extract_text(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    validate_file_type(file_path)

    extension = path.suffix.lower()

    # Plain text files do not have Docling page provenance.
    if extension in {".txt", ".md"}:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    converter = DocumentConverter()

    result = converter.convert(path)

    return result.document.export_to_markdown(
        page_break_placeholder=PAGE_BREAK_MARKER,
    )


def extract_and_save(
    file_path: str,
    output_path: str,
) -> Path:

    text = extract_text(file_path)

    output = Path(output_path)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        text,
        encoding="utf-8",
    )

    return output