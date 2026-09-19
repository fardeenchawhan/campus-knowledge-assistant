from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
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
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    year: int = Form(...),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is required.",
        )

    extension = Path(file.filename).suffix.lower()

    if extension != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
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

    unique_name = (
        f"{uuid4().hex}_{file.filename}"
    )

    pdf_path = upload_dir / unique_name

    with pdf_path.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            output.write(chunk)

    markdown_path = (
        extracted_dir
        / f"{pdf_path.stem}.md"
    )

    try:
        extract_and_save(
            file_path=str(pdf_path),
            output_path=str(markdown_path),
        )

        document_version = await ingest_document(
            db=db,
            markdown_path=str(markdown_path),
            title=title,
            source=str(pdf_path),
            year=year,
        )

    except Exception as exc:
        if pdf_path.exists():
            pdf_path.unlink()

        if markdown_path.exists():
            markdown_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {exc}",
        )

    return {
        "message": "Document uploaded successfully.",
        "document_id": document_version.document_id,
        "version": document_version.version_number,
        "file_name": document_version.file_name,
    }
