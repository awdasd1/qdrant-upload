# 🌐 دليل النشر على Coolify

## خطوات النشر السريعة

### 1️⃣ إنشاء المستودع على GitHub

```bash
# اضغط على النابط أدناه أو انسخ الرابط في المتصفح
https://github.com/new
```

**الإعدادات:**
- **Repository name**: `qdrant-upload`
- **Description**: Qdrant Upload Server for Legal Documents
- **Visibility**: Public ✅
- **Initialize repository**: فارغ (سنرفع الملفات)

ثم انقر **"Create repository"**

---

### 2️⃣ رفع المشروع إلى GitHub

```bash
# تشغيل السكريبت
bash push-to-github.sh

# أو يدويًا:
git remote add origin https://github.com/awdasd1/qdrant-upload.git
git branch -M main
git push -u origin main
```

**النتيجة المتوقعة:**
```
✅ Everything up-to-date
✅ تم الرفع بنجاح!
```

---

### 3️⃣ ربط Coolify

#### الخطوة أ: فتح Coolify

1. افتح لوحة تحكم Coolify: `https://your-coolify-instance.com`
2. سجل الدخول بحسابك

#### الخطوة ب: إضافة تطبيق جديد

1. انقر على **"Applications"** أو **"New Application"**
2. اختر **"GitHub Repository"**
3. إذا لم تكن متصلاً:
   - اختر **"Connect GitHub"**
   - ستُوجَّه إلى GitHub
   - اقبل الإذن
   - عُد إلى Coolify

#### الخطوة ج: اختيار المستودع

1. من القائمة، ابحث عن: `qdrant-upload`
2. أو اختره من البحث
3. اختر الفرع: **main**
4. انقر **"Next"** أو **"Continue"**

#### الخطوة د: تكوين البناء

اترك الإعدادات الافتراضية:

```
Build Pack: Nixpacks ✅
Port: 8000 ✅
```

#### الخطوة هـ: متغيرات البيئة

أضف المتغيرات التالية:

| المتغير | القيمة | ملاحظات |
|---------|--------|---------|
| `QDRANT_URL` | `http://qdrant:6333` | اترك الافتراضي |
| `ENVIRONMENT` | `production` | |
| `WORKERS` | `2` | حسب الموارد |
| `EMBED_API_KEY` | *(اختياري)* | مفتاح API الخاص بك |

#### الخطوة و: خدمات إضافية

قد تحتاج إلى Qdrant. **اختيارات:**

**A) الخيار الأول: Qdrant من Docker Hub**
```
اختر: Add Service
اختر: Qdrant
الصورة: qdrant/qdrant:latest
المنفذ: 6333
```

**B) الخيار الثاني: استخدام Qdrant محلي**
```
QDRANT_URL=http://your-qdrant-server:6333
```

#### الخطوة ز: النشر

1. انقر **"Deploy"** 🚀
2. انتظر البناء (3-10 دقائق)
3. تحقق من السجلات
4. افتح الرابط عند الانتهاء

---

## ✅ التحقق من النشر

### عند الانتهاء، يجب أن ترى:

```
✅ Build successful
✅ Deployment started
✅ Application is running
```

### اختبر التطبيق:

```bash
# استبدل URL الحقيقي
curl https://your-app-url.com/health
# النتيجة: {"status":"ok"}

# البحث
curl "https://your-app-url.com/search?q=عقد"
```

---

## 🔄 التحديثات التلقائية

**الآن عندما تقوم بـ push:**

```bash
git add .
git commit -m "Update feature"
git push origin main  # 🚀 ينشر تلقائياً على Coolify!
```

---

## 🐛 استكشاف الأخطاء

### المشكلة: الدمج فشل

**الحل:**
1. افتح قسم **"Logs"** في Coolify
2. ابحث عن رسالة الخطأ
3. شيوع الأخطاء:
   - `ModuleNotFoundError`: تحقق من `requirements.txt`
   - `Connection refused`: تحقق من `QDRANT_URL`
   - `TimeoutError`: زد وقت انتظار البناء

### المشكلة: الخدمة تتعطل بعد الدمج

**الحل:**
1. افتح **"Logs"** وابحث عن الخطأ
2. تحقق من المتغيرات البيئية
3. أعد النشر

### المشكلة: لا يمكن الوصول إلى التطبيق

**الحل:**
1. تحقق من أن النطاق يشير إلى Coolify
2. انتظر تأكيد SSL (قد يستغرق بضع دقائق)
3. افتح لوحة تحكم Coolify وتحقق من الحالة

---

## 📊 المراقبة

### في لوحة تحكم Coolify:

- **Status**: حالة التطبيق
- **Logs**: سجلات التطبيق
- **Metrics**: الاستخدام (CPU, RAM)
- **Deployments**: سجل النشر

### الأوامر المفيدة:

```bash
# عرض السجلات الأخيرة
docker logs <container-id>

# إعادة تشغيل
docker restart <container-id>

# حالة المستودع
cd /path/to/project && git status
```

---

## 🔒 الأمان

### نصائح مهمة:

✅ **أضف مفاتيح API إلى Coolify، لا إلى Git**
```
❌ خطأ: git push مع .env
✅ صحيح: متغيرات في لوحة Coolify
```

✅ **استخدم HTTPS فقط**
```
.env.example: QDRANT_URL=https://...
```

✅ **راقب الوصولات**
```
في لوحة Coolify: Settings > Security
```

---

## 📞 المساعدة

### موارد مفيدة:

- [توثيق Coolify](https://coolify.io/docs)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Nixpacks Buildpack](https://nixpacks.com/)

### الدعم:

- GitHub Issues: قسم المشاكل
- Coolify Discord: الدعم المباشر

---

**النشر ناجح! 🎉 تطبيقك الآن متاح على الإنترنت!**
