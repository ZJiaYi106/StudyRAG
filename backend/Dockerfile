# ============================================================
# StudyRAG 后端 Dockerfile
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（PyMuPDF 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 创建数据目录
RUN mkdir -p /app/data/uploads

# 复制应用代码
COPY . .

# FastAPI 默认端口
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
