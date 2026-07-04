# نشر مباشر على Coolify

## 1) رفع المشروع إلى GitHub

```bash
git add .
git commit -m "Prepare for Coolify deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/qdrant-upload.git
git push -u origin main
```

## 2) إنشاء التطبيق في Coolify

1. افتح Coolify
2. اختر New Application
3. اختر GitHub Repository
4. اربط حساب GitHub إذا لزم الأمر
5. اختر المستودع: `YOUR_USERNAME/qdrant-upload`
6. اختر الفرع: `main`

## 3) الإعدادات المطلوبة

- Build Pack: `Nixpacks`
- Port: `8000`
- Start Command: `python main.py`

## 4) متغيرات البيئة

أضف هذه القيم في قسم Environment:

```env
PORT=8000
HOST=0.0.0.0
ENVIRONMENT=production
WORKERS=1
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=
EMBED_API_KEY=
```

## 5) إذا أردت تشغيل Qdrant مع التطبيق

في Coolify، أضف خدمة أخرى من نوع Qdrant:

- Image: `qdrant/qdrant:latest`
- Port: `6333`

ثم استخدم في التطبيق:

```env
QDRANT_URL=http://qdrant:6333
```

## 6) النشر

انقر Deploy وانتظر حتى يكتمل البناء.

## 7) التحقق

بعد النشر، افتح:

```text
https://YOUR-APP-URL/health
```

يجب أن تعيد النتيجة:

```json
{"status":"ok"}
```

## 8) ملاحظات مهمة

- لا تضع مفاتيح حقيقية داخل Git
- استخدم Coolify Secrets أو Environment Variables
- إذا كان التطبيق لا يعمل، راجع Logs في Coolify
