from httpx import AsyncClient


async def test_health(client: AsyncClient):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy"
    }


async def test_database_health(client: AsyncClient):
    response = await client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": 1,
    }