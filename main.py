from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from src.core.database import get_db
from src.auth.router import router as auth_router
from src.rag.router import router as rag_router
from src.admin.router import router as admin_router

app = FastAPI(
    title="Campus Knowledge Assistant",
    description="Production-oriented RAG API for university knowledge.",
    version="1.0.0",
)

app.include_router(auth_router)
app.include_router(rag_router)
app.include_router(admin_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/health/db")
async def database_health_check(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("SELECT 1"))
    
    return {
        "status": "healthy",
        "database": result.scalar(),
    }
