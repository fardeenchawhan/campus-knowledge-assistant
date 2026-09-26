import asyncio

from src.core.database import AsyncSessionLocal
from src.ingestion.service import ingest_document


async def main():
    async with AsyncSessionLocal() as db:
        document_version = await ingest_document(
            db=db,
            markdown_path="data/extracted/UGC Guidelines 2018.md",
            title="UGC Regulations 2018",
            source="UGC",
            year=2018,
        )

        print(
            f"Document version created: "
            f"{document_version.id}"
        )


if __name__ == "__main__":
    asyncio.run(main())