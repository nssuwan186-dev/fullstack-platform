from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
import os
from pathlib import Path

from app import database, models, schemas
from app.config import settings
from app.processor import DataProcessor
from app.security import DataPolicyEngine
from app.auth import get_current_user

# --- Logging ---
structlog.configure(processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()])
log = structlog.get_logger()

# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup")
    await database.wait_for_db()
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    await database.engine.dispose()
    log.info("shutdown")

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# --- Middleware & Static Files ---
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# สร้างโฟลเดอร์ Output และ Mount สำหรับเข้าถึงไฟล์
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="output"), name="static")

processor = DataProcessor(output_dir=str(OUTPUT_DIR))
policy_engine = DataPolicyEngine()

# --- Endpoints ---

@app.get("/health")
async def health():
    return {"status": "online", "parallel_mode": "enabled"}

@app.post("/process/excel", status_code=202)
async def process_excel(
    data: list[dict], 
    background_tasks: BackgroundTasks, 
    user=Depends(get_current_user)
):
    """
    ใช้ BackgroundTasks เพื่อทำ Parallelism (ไม่รอให้ประมวลผลเสร็จแล้วค่อยตอบ)
    ระบบจะตอบรับทันที (202 Accepted) และไปรันงานหนักข้างหลัง
    """
    log.info("task_received", type="excel", user=user["username"])
    
    # ดำเนินการคัดกรองข้อมูลทันที (Fast)
    clean_data = policy_engine.process_mixed_data(data)
    
    # ส่งงานหนัก (CPU Bound) ไปทำใน Background thread
    filename = f"secure_{user['username']}_{os.urandom(4).hex()}.xlsx"
    background_tasks.add_task(processor.process_excel_with_formulas, clean_data, filename)
    
    return {
        "message": "Task accepted and processing in background",
        "expected_file": filename,
        "download_url": f"/files/{filename}"
    }

@app.get("/users/search", response_model=list[schemas.User], dependencies=[Depends(get_current_user)])
async def search_users(
    q: str | None = None, 
    is_active: bool = True, 
    skip: int = 0, 
    limit: int = 10,
    db: AsyncSession = Depends(database.get_db)
):
    """
    ค้นหา User พร้อมระบบ Type Conversion:
    - is_active: แปลงจาก 'true', '1', 'on' เป็น True อัตโนมัติ
    - skip, limit: แปลงเป็น int และตรวจสอบว่าเป็นตัวเลขหรือไม่
    """
    log.info("user_search", query=q, is_active=is_active, limit=limit)
    
    query = select(models.User).where(models.User.is_active == is_active)
    
    if q:
        query = query.where(models.User.email.contains(q))
    
    result = await db.execute(query.offset(skip).limit(limit))
    users = result.scalars().all()
    return users

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
