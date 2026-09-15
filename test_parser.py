from pathlib import Path

from src.ingestion.chunker import chunk_markdown


text = Path(
    "data/extracted/UGC Guidelines 2018.md"
).read_text(encoding="utf-8")


chunks = chunk_markdown(text)

print(f"Total chunks: {len(chunks)}")

print("\n" + "=" * 80)

for chunk in chunks:
    if any(
        section in chunk.content
        for section in [
            "Section: 3.4",
            "Section: 3.5",
            "Section: 3.7",
            "Section: 3.8",
            "Section: 3.12",
        ]
    ):
        print("\n" + "=" * 80)
        print(f"CHUNK {chunk.chunk_index}")
        print(chunk.content)