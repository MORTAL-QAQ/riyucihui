FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (使用阿里云镜像加速)
# fonts-wqy-microhei: 文泉驿微米黑 TrueType，完整中日韩字符集，ReportLab 兼容
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    apt-get update && apt-get install -y --no-install-recommends \
    curl libxml2 fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy frontend static files (served by FastAPI)
COPY frontend/ /frontend/

# Create data directory for SQLite database
RUN mkdir -p /app/data

# 非 root 运行（#8）：创建 appuser；entrypoint 以 root 启动修正数据卷属主后降权
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app /frontend

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--limit-max-requests", "5000", "--timeout-keep-alive", "60"]
