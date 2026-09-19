from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.core.database import get_db
from src.rag.schemas import AskRequest, AskResponse
from src.rag.service import answer_question


router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)


@router.post(
    "/ask",
    response_model=AskResponse,
)
async def ask_question(
    request: AskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await answer_question(
        db=db,
        question=request.question,
        role=current_user.role,
    )

    return AskResponse(
        answer=result['answer'],
        sources=result["sources"],
    )