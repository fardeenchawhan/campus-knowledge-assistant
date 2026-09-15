import asyncio

import src.models.registry
from src.core.database import AsyncSessionLocal
from src.rag.service import answer_question


async def main():


    question = "What are the minimum qualifications for appointment of teachers?"

    async with AsyncSessionLocal() as db:

        answer = await answer_question(
            db=db,
            question=question,
        )

        print("\nQUESTION:")
        print(question)

        print("\nANSWER:")
        print(answer)


if __name__ == "__main__":
    asyncio.run(main())