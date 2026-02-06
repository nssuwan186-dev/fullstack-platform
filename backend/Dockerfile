FROM python:3.12-slim

WORKDIR /app

# ติดตั้ง uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 1. เตรียม Dependencies (Layer caching)
COPY pyproject.toml .
RUN uv sync --frozen --no-dev

# 2. Copy Source และ Build เป็น Package
COPY app ./app
COPY README.md .

# ติดตั้งโปรเจกต์ตัวเองเป็น Package (ตาม uv documentation ที่ส่งมา)
# วิธีนี้จะสร้าง .dist-info ทำให้ตรวจสอบความสมบูรณ์ได้ง่าย
RUN uv pip install .

# 3. ตรวจสอบความสมบูรณ์ก่อนรัน (Health Check Script)
RUN python -c "import os; \
    exists = any(d.endswith('.dist-info') for d in os.listdir('/app/.venv/lib/python3.12/site-packages')); \
    print('Dependencies Verified' if exists else exit(1))"

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
