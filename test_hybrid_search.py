import asyncio

import src.models.registry

from src.core.database import AsyncSessionLocal
from src.retrieval.hybrid_search import hybrid_search


async def main():

    query = "What are the minimum qualifications for appointment of teachers?"

    async with AsyncSessionLocal() as db:

        results = await hybrid_search(
            db=db,
            query=query,
            top_k=5,
            candidate_k=10,
        )

        print(f"\nQuery: {query}\n")

        for chunk, score in results:

            print("=" * 80)
            print(f"Chunk: {chunk.chunk_index}")
            print(f"RRF Score: {score:.6f}")
            print("=" * 80)

            print(chunk.content[:1000])
            print()


if __name__ == "__main__":
    asyncio.run(main())