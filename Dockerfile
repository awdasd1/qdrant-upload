FROM python:3.11-slim

WORKDIR /app

# تثبيت المتطلبات النظام
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# نسخ ملفات المتطلبات
COPY requirements.txt .

# تثبيت مكتبات Python
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir sentence-transformers qdrant-client uvicorn

# نسخ كود التطبيق
COPY . .

# إنشاء مجلدات ضرورية
RUN mkdir -p uploads logs

# تحديد المستخدم بدون صلاحيات root (أمان)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# تعريض المنفذ
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# تشغيل التطبيق
CMD ["uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8000"]
