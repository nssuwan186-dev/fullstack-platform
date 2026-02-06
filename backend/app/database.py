from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.config import settings
import structlog
import asyncio

log = structlog.get_logger()

# สร้าง Engine
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False, # ปิด Echo ใน Prod เพื่อ Log ไม่รก
    pool_pre_ping=True, # ตรวจสอบ Connection ก่อนใช้เสมอ (กัน Error connection lost)
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            log.error("db_session_error", error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()

async def wait_for_db():
    """ฟังก์ชันสำหรับรอ Database ให้พร้อมก่อนเริ่มแอป"""
    max_retries = 10 # ลองเชื่อมต่อ 10 ครั้ง
    wait_seconds = 2
    
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            log.info("db_connected_successfully")
            return
        except Exception as e:
            log.warning("db_connection_retry", attempt=attempt+1, error=str(e))
            await asyncio.sleep(wait_seconds)
            
    log.error("db_connection_failed_final")
    raise Exception("Could not connect to database after multiple retries")
