import sys
from pathlib import Path
import os
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio

from src.core.database import AsyncSessionLocal
from src.ingestion.service import ingest_document

async def main():
    async with AsyncSessionLocal() as db:
        document_version = await ingest_document(
            db=db,
            markdown_path="data/extracted/204146b0697643e8b58af04ec6267509.md",
            title="UGC Regulations 2018 Remote Test",
            source="UGC remote ingestion test",
            year=2018,
            document_key="ugc-regulations-2018-remote-test",
        )

        print(f"Document version ID: {document_version.id}")
        print(f"Version number: {document_version.version_number}")
        print(f"Current version: {document_version.is_current}")

if __name__ == "__main__":
    asyncio.run(main())

