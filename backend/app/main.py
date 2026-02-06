from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
import time

from app import database, models, schemas
from app.config import settings
from app.api import router # เดี๋ยวเราจะย้าย Route ไปไฟล์แยกเพื่อความเป็นระเบียบ

# --- Logging Configuration ---
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
log = structlog.get_logger()

# --- Lifespan (Startup/Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup_initiated")
    
    # 1. รอ Database
    await database.wait_for_db()
    
    # 2. สร้างตาราง (Auto-migrate สำหรับ Dev)
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
        
    log.info("startup_complete")
    yield
    log.info("shutdown_initiated")
    await database.engine.dispose()
    log.info("shutdown_complete")

# --- App Init ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        log.info(
            "api_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration=f"{process_time:.4f}s"
        )
        return response
    except Exception as e:
        log.error("request_failed", error=str(e), path=request.url.path)
        raise

# --- Global Error Handlers ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error("unhandled_exception", error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal Server Error. We are monitoring this issue."},
    )

# --- Routes ---
# เราจะย้าย Logic เดิมไปไว้ที่ Route แยก เพื่อไม่ให้ main.py รก
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

api_router = APIRouter()

@api_router.get("/")
async def root():
    return {"message": "System is running", "status": "healthy"}

@api_router.post("/users/", response_model=schemas.User)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(database.get_db)):
    # ... logic เดิม ...
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    if result.scalar_one_or_none():
         # คืนค่า Error ที่ถูกต้อง ไม่ใช่ 500
         return JSONResponse(
             status_code=400, 
             content={"detail": "Email already exists"}
         )
    
    new_user = models.User(email=user.email, hashed_password=user.password + "hash")
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

app.include_router(api_router, prefix=settings.API_V1_STR)
