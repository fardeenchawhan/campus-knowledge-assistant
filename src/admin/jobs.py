import asyncio
import json
from pathlib import Path
import logging
from src.core.database import AsyncSessionLocal
from src.core.redis import redis_client
from src.ingestion.parser import extract_and_save
from src.ingestion.service import ingest_document
from src.ingestion.hash import calculate_file_hash

logger = logging.getLogger(__name__)

JOB_TTL = 24 * 60 * 60


async def update_job(
    job_id: str,
    *,
    status: str,
    progress: int,
    message: str,
    **extra,
) -> None:

    key = f"document_job:{job_id}"

    data = {
        "job_id": job_id,
        "status": status,
        "progress": progress,
        "message": message,
        **extra,
    }

    await redis_client.set(
        key,
        json.dumps(data),
        ex=JOB_TTL,
    )


async def get_job(job_id: str) -> dict | None:

    key = f"document_job:{job_id}"

    data = await redis_client.get(key)

    if data is None:
        return None

    return json.loads(data)


async def process_document_job(
    *,
    job_id: str,
    file_path: str,
    markdown_path: str,
    title: str,
    document_key: str,
    year: int,
    access_level: str,
    original_filename: str,
) -> None:

    try:

        await update_job(
            job_id,
            status="processing",
            progress=10,
            message="Extracting document content...",
        )

        # Docling is synchronous and potentially CPU-heavy,
        # so run it outside the async event loop.
        await asyncio.to_thread(
            extract_and_save,
            file_path,
            markdown_path,
        )


        await update_job(
            job_id,
            status="processing",
            progress=35,
            message="Document extraction completed. Creating chunks...",
        )


        async with AsyncSessionLocal() as db:

            source_hash = await asyncio.to_thread(
                calculate_file_hash,
                file_path,
            )

            await ingest_document(
                db=db,
                markdown_path=markdown_path,
                title=title,
                source=file_path,
                source_file_name=original_filename,
                document_key=document_key,
                year=year,
                access_level=access_level,
                source_hash=source_hash,
            )


        await update_job(
            job_id,
            status="completed",
            progress=100,
            message="Document processing completed successfully.",
        )


    except Exception as exc:

        await update_job(
            job_id,
            status="failed",
            progress=100,
            message=f"Document processing failed: {exc}",
        )

        # Keep the original exception visible in the
        # server logs for debugging.
        logger.info(
            f"Document job {job_id} failed: {exc}"
        )