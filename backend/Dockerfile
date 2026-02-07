FROM python:3.12-slim

WORKDIR /app

# ติดตั้ง uv (มาตรฐานใหม่สำหรับ Virtual Environments ตาม docs)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 1. สร้างและจัดการ Virtual Environment
COPY pyproject.toml .
RUN uv sync --frozen --no-dev

# 2. ติดตั้ง Source Code
COPY app ./app
COPY README.md . 

# สร้างโฟลเดอร์สำหรับเก็บผลลัพธ์
RUN mkdir -p output

# 3. รันผ่าน uv (ซึ่งจะเรียกใช้ Virtual Environment ที่สร้างไว้โดยอัตโนมัติ)
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
