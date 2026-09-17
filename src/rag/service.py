from sqlalchemy.ext.asyncio import AsyncSession

from src.rag.context import build_context
from src.rag.llm import generate_answer
from src.retrieval.reranker import reranked_search
from src.auth.models import UserRole

async def answer_question(
    db: AsyncSession,
    question: str,
    role:UserRole,
    top_k: int = 5,
) -> str:

    results = await reranked_search(
        db=db,
        query=question,
        role=role,
        top_k=top_k,
        candidate_k=30,
    )

    chunks = [
        chunk
        for chunk, _ in results
    ]

    if not chunks:
        return "I don't know based on the available university documents."

    context = build_context(chunks)

    answer = await generate_answer(
        question=question,
        context=context,
    )

    return answer