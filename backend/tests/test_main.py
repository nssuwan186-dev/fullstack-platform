import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import engine, Base

@pytest.fixture(scope="module")
async def db_engine():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_read_root():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to FullStack Platform API"}

@pytest.mark.asyncio
async def test_create_user(db_engine):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/users/", json={"email": "test@example.com", "password": "password"})
@pytest.mark.asyncio
async def test_search_users_query_params(db_engine):
    headers = {"X-API-Key": "dev-secret-key-123"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # ทดสอบส่ง bool และ int แบบต่างๆ
        response = await ac.get("/api/v1/users/search?is_active=1&limit=5", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) <= 5

@pytest.mark.asyncio
async def test_search_users_invalid_type(db_engine):
    headers = {"X-API-Key": "dev-secret-key-123"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # ส่ง 'abc' เข้าไปในฟิลด์ที่ต้องการ int (limit)
        response = await ac.get("/api/v1/users/search?limit=abc", headers=headers)
    assert response.status_code == 422 # Validation Error อัตโนมัติจาก FastAPI
