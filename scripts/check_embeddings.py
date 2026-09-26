import asyncio

# Register all SQLAlchemy models before using them.
import src.models.registry

from src.core.database import AsyncSessionLocal
from src.embeddings.database import embed_chunks


async def main():
    async with AsyncSessionLocal() as db:
        total = await embed_chunks(db)

        print(
            f"\nSuccessfully embedded {total} chunks."
        )


if __name__ == "__main__":
    asyncio.run(main())