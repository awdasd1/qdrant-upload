#!/usr/bin/env python3
"""
نقطة الدخول الرئيسية للتطبيق
Entry point for Qdrant Upload Application
"""

import os
import sys
import uvicorn

if __name__ == "__main__":
    # تحديد المتغيرات البيئية
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    workers = int(os.getenv("WORKERS", "1"))
    
    # تسجيل إعدادات التشغيل
    print(f"🚀 Starting Qdrant Upload Server...")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Reload: {reload}")
    print(f"   Workers: {workers}")
    
    # تشغيل التطبيق
    uvicorn.run(
        "mcp_server:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        access_log=True,
    )
