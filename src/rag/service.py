import re

from sqlalchemy.ext.asyncio import AsyncSession

from src.rag.context import build_context
from src.rag.llm import generate_answer
from src.retrieval.reranker import reranked_search
from src.auth.models import UserRole


UNKNOWN_ANSWER = "I don't know based on the available university documents."


def clean_answer(answer: str) -> str:
    """
    Normalize the LLM response while preserving useful Markdown formatting.
    """

    # Normalize Windows-style line endings
    answer = answer.replace("\r\n", "\n").replace("\r", "\n")

    # Remove trailing whitespace from each line
    answer = "\n".join(line.rstrip() for line in answer.split("\n"))

    # Prevent excessive blank lines
    answer = re.sub(r"\n{3,}", "\n\n", answer)

    return answer.strip()


def extract_valid_citations(
    answer: str,
    sources: list[dict],
) -> tuple[str, list[dict]]:
    """
    Validate [Source N] and 【Source N】 citations against the
    sources actually provided to the LLM.

    Supports:
        [Source 1]
        [Source 1, Source 4]
        【Source 4】
        【Source 1, Source 4, Source 2】

    Returns:
        cleaned answer
        only the sources actually cited by the answer
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
        # Extract every source number from the citation.
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

        # If the citation contains no valid sources, remove it.
        if not valid_numbers:
            return ""

        # Normalize all citation formats to [Source N].
        return "[" + ", ".join(
            f"Source {number}"
            for number in valid_numbers
        ) + "]"

    cleaned_answer = citation_pattern.sub(
        replace_citation,
        answer,
    )

    cleaned_answer = clean_answer(cleaned_answer)

    # Return sources in the order they first appeared in the answer.
    cited_sources = [
        next(
            source
            for source in sources
            if source["source_number"] == source_number
        )
        for source_number in cited_source_numbers
    ]

    return cleaned_answer, cited_sources


async def answer_question(
    db: AsyncSession,
    question: str,
    role: UserRole,
    top_k: int = 5,
) -> dict:

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
        return {
            "answer": UNKNOWN_ANSWER,
            "sources": [],
        }

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

    return {
        "answer": answer,
        "sources": cited_sources,
    }