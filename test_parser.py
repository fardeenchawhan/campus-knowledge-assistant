from pathlib import Path

from src.ingestion.chunker import chunk_markdown


MARKDOWN_PATH = Path(
    "data/extracted/UGC Guidelines 2018.md"
)


text = MARKDOWN_PATH.read_text(
    encoding="utf-8"
)

chunks = chunk_markdown(
    text,
    max_characters=1500,
)

print(f"Total chunks: {len(chunks)}")

for chunk in chunks[:5]:
    print("\n" + "=" * 80)
    print(f"CHUNK {chunk.chunk_index}")
    print("=" * 80)
    print(chunk.content)