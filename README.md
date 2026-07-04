# 📚 Qdrant Upload - تطبيق رفع المواد القانونية إلى Qdrant

تطبيق حديث لرفع ومعالجة المواد القانونية إلى قاعدة بيانات Qdrant المتقدمة للبحث الدلالي.

**[English](#english) | [العربية](#العربية)**

---

## العربية

### 📋 نظرة عامة

تطبيق FastAPI متكامل يوفر:
- ✅ رفع البيانات إلى Qdrant مع معالجة نصية متقدمة
- ✅ واجهة ويب تفاعلية للبحث عن المواد القانونية
- ✅ دعم التضمينات المحلية و API الخارجية
- ✅ معالجة التشكيل العربي تلقائياً
- ✅ نشر سحابي على Coolify/Docker

### 🚀 البدء السريع

#### مع Docker Compose (الأسهل)

```bash
# 1. استنساخ المستودع
git clone https://github.com/awdasd1/qdrant-upload.git
cd qdrant-upload

# 2. إعداد البيئة
cp .env.example .env

# 3. تشغيل التطبيق والـ Qdrant معاً
docker-compose up -d

# 4. الوصول إلى التطبيق
# الويب: http://localhost:8000
# Qdrant: http://localhost:6333
```

#### بدون Docker

```bash
# 1. تفعيل البيئة الافتراضية
python -m venv venv
source venv/bin/activate

# 2. تثبيت المتطلبات
pip install -r requirements.txt
pip install sentence-transformers qdrant-client uvicorn

# 3. تشغيل Qdrant (في طرفية منفصلة)
docker run -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant

# 4. تشغيل التطبيق
python main.py
```

### 📁 هيكل المشروع

```
qdrant-upload/
├── main.py                 # 🎯 نقطة الدخول الرئيسية
├── mcp_server.py          # 🌐 خادم FastAPI
├── qdrant_upload.py       # 📤 سكريبت الرفع
├── requirements.txt       # 📦 المكتبات
├── Dockerfile             # 🐳 Docker
├── docker-compose.yml     # 🔗 Docker Compose
├── coolify.json           # ☁️  تكوين Coolify
├── nixpacks.toml          # 🔨 تكوين Buildpack
├── .env.example           # ⚙️  متغيرات البيئة
├── .gitignore             # 📝 Git
├── moaamlat.json          # 📊 البيانات
└── static/                # 🎨 الويب
```

### ⚙️ متغيرات البيئة

انسخ `.env.example` إلى `.env`:

```bash
cp .env.example .env
```

ثم عدّل القيم:

```bash
# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-api-key

# Embeddings (اختياري)
EMBED_API_KEY=your-embed-key
EMBED_API_URL=https://api.cohere.com/v1/embed

# التطبيق
PORT=8000
ENVIRONMENT=production
WORKERS=1
```

### 🌐 النشر على Coolify

#### الخطوة 1️⃣: رفع إلى GitHub

```bash
# تهيئة المستودع
git init
git add .
git commit -m "Initial commit: Qdrant Upload Application"
git branch -M main
git remote add origin https://github.com/awdasd1/qdrant-upload.git
git push -u origin main
```

#### الخطوة 2️⃣: ربط مع Coolify

1. **فتح لوحة Coolify** وسجل الدخول
2. **اختر** "New Application"
3. **اختر** "GitHub Repository"
4. **ربط الحساب** وحدد المستودع: `awdasd1/qdrant-upload`
5. **تحديد الإعدادات**:
   - **Build Pack**: `Nixpacks` ✅
   - **Port**: `8000`
   - **Start Command**: `python main.py`
6. **إضافة متغيرات البيئة** من قسم "Environment"
7. **انقر** "Deploy" 🚀

#### الخطوة 3️⃣: التحديثات التلقائية

كل `git push` إلى `main` سيؤدي إلى نشر تلقائي! 

```bash
# بعد كل تحديث
git push origin main  # ينشر تلقائياً على Coolify
```

### 🛠️ أوامر مهمة

```bash
# تشغيل مع Docker
docker-compose up -d

# إيقاف التطبيق
docker-compose down

# عرض السجلات
docker-compose logs -f app

# بناء يدوي
docker build -t qdrant-upload:latest .

# تشغيل الرفع
python qdrant_upload.py --collection moaamlat --batch 128

# مع API خارجي
EMBED_API_KEY=your-key python qdrant_upload.py --embed-api-url "https://api.cohere.com/v1/embed"
```

### 📊 واجهة البرمجة (API)

```bash
# البحث
GET /search?q=عقد&limit=10

# مادة محددة
GET /article/{id}

# رفع ملف
POST /upload
Content-Type: multipart/form-data
file: <binary>

# الحالة
GET /health
```

### 🔒 الأمان

✅ استخدم متغيرات البيئة للمفاتيح  
✅ لا تضع `.env` في Git  
✅ استخدم HTTPS في الإنتاج  
✅ قيّد صلاحيات Qdrant  

### 📦 المتطلبات

- Python 3.8+
- Docker (اختياري)
- 2GB RAM
- اتصال إنترنت

### 🐛 استكشاف الأخطاء

**Qdrant غير متصل:**
```bash
curl http://localhost:6333/collections
```

**نموذج بطيء:**
```bash
# استخدم نموذج أخف في .env
EMBED_MODEL=all-MiniLM-L6-v2
```

---

## English

### 📋 Overview

A complete FastAPI application for uploading legal documents to Qdrant vector database:

- ✅ Upload legal data with advanced text processing
- ✅ Interactive web interface for searching
- ✅ Support for local and external embeddings
- ✅ Automatic Arabic diacritical handling
- ✅ Cloud deployment on Coolify/Docker

### 🚀 Quick Start

```bash
# Clone
git clone https://github.com/awdasd1/qdrant-upload.git
cd qdrant-upload

# Run with Docker
docker-compose up -d

# Access
# Web: http://localhost:8000
# API: http://localhost:6333
```

### 🌐 Deploy to Coolify

1. Push to GitHub
2. Connect repository in Coolify dashboard
3. Select Nixpacks buildpack
4. Add environment variables
5. Deploy automatically

### 🛠️ Key Commands

```bash
# Start locally
python main.py

# Upload data
python qdrant_upload.py --collection moaamlat --batch 128

# Build Docker image
docker build -t qdrant-upload:latest .

# View logs
docker-compose logs -f
```

### 📦 Requirements

- Python 3.8+
- Docker (optional)
- 2GB RAM
- Internet connection

---

**Made with ❤️ for Legal Tech**

## 🔧 خيارات السكريبت

```
--collection: اسم المجموعة في Qdrant (افتراضي: moaamlat)
--qdrant-url: رابط Qdrant (افتراضي: http://127.0.0.1:6333)
--batch: حجم الدفعة (افتراضي: 3000)
--model: نموذج التضمينات (افتراضي: all-MiniLM-L6-v2)
--embed-api-url: رابط API التضمينات (اختياري)
--embed-api-key: مفتاح API (اختياري)
--input-file: مسار ملف الإدخال (اختياري)
--system-name: اسم النظام القانوني (اختياري)
--upload-mode: طريقة الرفع (overwrite/append, افتراضي: overwrite)
```

## ✅ متطلبات

- Python 3.8+
- Docker (لتشغيل Qdrant)
- ~2GB RAM
- اتصال إنترنت (لتحميل نماذج التضمينات الأولى)

---

**ملاحظة**: للحصول على أداء أفضل، استخدم GPU مع `sentence-transformers`
