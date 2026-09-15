from openai import AsyncOpenAI

from src.core.config import settings


client = AsyncOpenAI(
    api_key=settings.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)


SYSTEM_PROMPT = """
You are the Campus Knowledge Assistant.

Your job is to answer questions using ONLY the provided
university document context.

Rules:

1. Use only the supplied context.
2. Do not use outside knowledge.
3. Do not invent or assume information.
4. If the context does not contain enough information to answer
   the question, say:
   "I don't know based on the available university documents."
5. Keep the answer clear and concise.
6. Cite the sources using the source numbers provided in the context.
"""


async def generate_answer(
    question: str,
    context: str,
) -> str:

    response = await client.chat.completions.create(
        model="openai/gpt-oss-20b",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": (
                    f"Context:\n\n{context}\n\n"
                    f"Question:\n{question}"
                ),
            },
        ],
    )

    return response.choices[0].message.content or ""