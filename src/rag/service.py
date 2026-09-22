
import hashlib
import json
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import UserRole
from src.chunks.models import Chunk
from src.core.redis import redis_client
from src.documents.models import DocumentVersion
from src.rag.context import build_context
from src.rag.llm import generate_answer
from src.retrieval.reranker import reranked_search


UNKNOWN_ANSWER = "I don't know based on the available university documents."

RAG_CACHE_TTL = 10 * 60  # 10 minutes


def clean_answer(answer: str) -> str:
    """
    Normalize the LLM response while preserving useful Markdown formatting.
    """

    answer = answer.replace("\r\n", "\n").replace("\r", "\n")

    answer = "\n".join(
        line.rstrip()
        for line in answer.split("\n")
    )

    answer = re.sub(r"\n{3,}", "\n\n", answer)

    return answer.strip()


def extract_valid_citations(
    answer: str,
    sources: list[dict],
) -> tuple[str, list[dict]]:
    """
    Validate [Source N] and 【Source N】 citations against the
    sources actually provided to the LLM.
    """

    valid_source_numbers = {
        source["source_number"]
        for source in sources
    }

    cited_source_numbers = []

    citation_pattern = re.compile(
        r"[\[【]\s*"
        r"Source\s+(\d+)"
        r"(?:\s*,\s*Source\s+(\d+))*"
        r"\s*[\]】]",
        flags=re.IGNORECASE,
    )

    def replace_citation(match: re.Match) -> str:
        citation_text = match.group(0)

        numbers = re.findall(
            r"Source\s+(\d+)",
            citation_text,
            flags=re.IGNORECASE,
        )

        valid_numbers = []

        for number in numbers:
            source_number = int(number)

            if source_number in valid_source_numbers:
                valid_numbers.append(source_number)

                if source_number not in cited_source_numbers:
                    cited_source_numbers.append(source_number)

        if not valid_numbers:
            return ""

        return "[" + ", ".join(
            f"Source {number}"
            for number in valid_numbers
        ) + "]"

    cleaned_answer = citation_pattern.sub(
        replace_citation,
        answer,
    )

    cleaned_answer = clean_answer(cleaned_answer)

    cited_sources = [
        next(
            source
            for source in sources
            if source["source_number"] == source_number
        )
        for source_number in cited_source_numbers
    ]

    return cleaned_answer, cited_sources


async def get_document_state(db: AsyncSession) -> str:
    """
    Return a value representing the current document/version state.

    The value changes whenever the set of document versions changes,
    allowing old RAG cache entries to naturally become invalid.
    """

    result = await db.execute(
        select(
            func.count(DocumentVersion.id),
            func.max(DocumentVersion.id),
        )
    )

    version_count, max_version_id = result.one()

    return f"{version_count}:{max_version_id or 0}"


def build_cache_key(
    *,
    question: str,
    role: UserRole,
    document_state: str,
    top_k: int,
) -> str:
    """
    Build a stable Redis key for a RAG response.
    """

    normalized_question = " ".join(
        question.strip().lower().split()
    )

    question_hash = hashlib.sha256(
        normalized_question.encode("utf-8")
    ).hexdigest()

    return (
        f"rag:v1:"
        f"{role.value}:"
        f"{top_k}:"
        f"{document_state}:"
        f"{question_hash}"
    )


async def answer_question(
    db: AsyncSession,
    question: str,
    role: UserRole,
    top_k: int = 5,
) -> dict:

    # ---------------------------------------------------------
    # 1. Build cache key
    # ---------------------------------------------------------

    document_state = await get_document_state(db)

    cache_key = build_cache_key(
        question=question,
        role=role,
        document_state=document_state,
        top_k=top_k,
    )

    # ---------------------------------------------------------
    # 2. Check Redis
    # ---------------------------------------------------------

    cached_result = await redis_client.get(cache_key)

    if cached_result:
        return json.loads(cached_result)

    # ---------------------------------------------------------
    # 3. Run normal RAG pipeline
    # ---------------------------------------------------------

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
        result = {
            "answer": UNKNOWN_ANSWER,
            "sources": [],
        }

        await redis_client.set(
            cache_key,
            json.dumps(result),
            ex=RAG_CACHE_TTL,
        )

        return result

    context, sources = build_context(chunks)

    answer = await generate_answer(
        question=question,
        context=context,
    )

    answer = clean_answer(answer)

    answer, cited_sources = extract_valid_citations(
        answer=answer,
        sources=sources,
    )

    result = {
        "answer": answer,
        "sources": cited_sources,
    }

    # ---------------------------------------------------------
    # 4. Store final result in Redis
    # ---------------------------------------------------------

    await redis_client.set(
        cache_key,
        json.dumps(result),
        ex=RAG_CACHE_TTL,
    )

    return result