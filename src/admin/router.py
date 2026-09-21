from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from src.admin.jobs import (
    get_job,
    process_document_job,
    update_job,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import HTMLResponse
from src.auth.models import User, UserRole
from src.auth.rbac import require_roles
from src.core.config import settings
from src.core.database import get_db
from src.documents.models import Document, DocumentVersion
from src.ingestion.parser import extract_and_save
from src.ingestion.service import ingest_document

SUPPORTED_UPLOAD_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".html",
    ".htm",
    ".md",
    ".txt",
}

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.get("/dashboard")
async def dashboard(
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
    db: AsyncSession = Depends(get_db),
):
    documents_result = await db.execute(
        select(Document)
    )

    documents = documents_result.scalars().all()

    users_result = await db.execute(
        select(User)
    )

    users = users_result.scalars().all()

    professors = [
        user
        for user in users
        if user.role == UserRole.PROFESSOR
    ]

    return {
        "documents": len(documents),
        "users": len(users),
        "professors": len(professors),
        "active_users": sum(
            user.is_active
            for user in users
        ),
    }


@router.get("/documents")
async def list_documents(
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document)
        .order_by(Document.created_at.desc())
    )

    documents = result.scalars().all()

    response = []

    for document in documents:

        current_version_result = await db.execute(
            select(DocumentVersion)
            .where(
                DocumentVersion.document_id == document.id,
                DocumentVersion.is_current.is_(True),
            )
        )

        current_version = (
            current_version_result
            .scalar_one_or_none()
        )

        response.append(
            {
                "id": document.id,
                "title": document.title,
                "source": document.source,
                "current_version": (
                    current_version.version_number
                    if current_version
                    else None
                ),
                "created_at": document.created_at,
                "updated_at": document.updated_at,
            }
        )

    return response


@router.get(
    "/",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def admin_page():
    template_path = (
        Path(__file__).parent
        / "templates"
        / "dashboard.html"
    )

    return template_path.read_text(
        encoding="utf-8"
    )


@router.post(
    "/documents/upload",
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    year: int = Form(...),
    document_key: str = Form(...),
    access_level: str = Form("student"),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is required.",
        )

    document_key = document_key.strip()

    if not document_key:
        raise HTTPException(
            status_code=400,
            detail="Document key is required.",
        )


    # Prevent paths such as:
    # ../../something.pdf
    original_filename = Path(
        file.filename
    ).name


    extension = Path(
        original_filename
    ).suffix.lower()


    if extension not in SUPPORTED_UPLOAD_EXTENSIONS:
        supported = ", ".join(
            sorted(SUPPORTED_UPLOAD_EXTENSIONS)
        )

        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: {extension}. "
                f"Supported types: {supported}"
            ),
        )


    if access_level not in {
        "student",
        "professor",
        "admin",
    }:
        raise HTTPException(
            status_code=400,
            detail="Invalid access level.",
        )


    if year < 1900 or year > 2100:
        raise HTTPException(
            status_code=400,
            detail="Invalid document year.",
        )


    upload_dir = Path(
        settings.DOCUMENT_UPLOAD_DIR
    )

    extracted_dir = Path(
        settings.DOCUMENT_EXTRACTED_DIR
    )


    upload_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    extracted_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    job_id = uuid4().hex


    saved_filename = (
        f"{job_id}_{original_filename}"
    )

    file_path = (
        upload_dir / saved_filename
    )


    markdown_path = (
        extracted_dir
        / f"{job_id}.md"
    )


    max_size = (
        settings.MAX_UPLOAD_SIZE_MB
        * 1024
        * 1024
    )


    bytes_written = 0


    try:

        with file_path.open("wb") as output:

            while True:

                chunk = await file.read(
                    1024 * 1024
                )

                if not chunk:
                    break


                bytes_written += len(chunk)


                if bytes_written > max_size:

                    output.close()

                    if file_path.exists():
                        file_path.unlink()

                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"File is too large. "
                            f"Maximum size is "
                            f"{settings.MAX_UPLOAD_SIZE_MB} MB."
                        ),
                    )


                output.write(chunk)


    except HTTPException:
        raise

    except Exception as exc:

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to save uploaded file: "
                f"{exc}"
            ),
        )


    await update_job(
        job_id,
        status="queued",
        progress=0,
        message="Document uploaded. Waiting for processing...",
        filename=original_filename,
        title=title,
        document_key=document_key,
    )


    background_tasks.add_task(
        process_document_job,
        job_id=job_id,
        file_path=str(file_path),
        markdown_path=str(markdown_path),
        title=title,
        document_key=document_key,
        year=year,
        access_level=access_level,
        original_filename=original_filename,
    )


    return {
        "message": "Document uploaded and processing started.",
        "job_id": job_id,
        "status": "queued",
        "filename": original_filename,
    }


@router.get(
    "/documents/jobs/{job_id}"
)
async def document_job_status(
    job_id: str,
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
):
    job = await get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Document processing job not found.",
        )

    return job