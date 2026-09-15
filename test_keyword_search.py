import asyncio

import src.models.registry

from src.core.database import AsyncSessionLocal
from src.retrieval.keyword_search import keyword_search


async def main():

    query = "minimum qualifications appointment teachers"

    async with AsyncSessionLocal() as db:

        results = await keyword_search(
            db=db,
            query=query,
            top_k=5,
        )

        print(f"\nQuery: {query}\n")

        for chunk, score in results:

            print("=" * 80)
            print(f"Chunk: {chunk.chunk_index}")
            print(f"Rank: {score:.4f}")
            print("=" * 80)

            print(chunk.content[:1000])
            print()


if __name__ == "__main__":
    asyncio.run(main())