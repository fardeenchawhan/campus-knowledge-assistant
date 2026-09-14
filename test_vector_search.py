import asyncio

# Register all SQLAlchemy models first.
import src.models.registry

from src.core.database import AsyncSessionLocal
from src.retrieval.vector_search import vector_search


async def main():
    query = "What are the minimum qualifications for appointment of teachers?"

    async with AsyncSessionLocal() as db:
        results = await vector_search(
            db=db,
            query=query,
            top_k=5,
        )

        print(f"\nQuery: {query}\n")

        for chunk, score in results:
            print("=" * 80)
            print(f"Chunk: {chunk.chunk_index}")
            print(f"Similarity: {score:.4f}")
            print("=" * 80)
            print(chunk.content[:1000])
            print()


if __name__ == "__main__":
    asyncio.run(main())