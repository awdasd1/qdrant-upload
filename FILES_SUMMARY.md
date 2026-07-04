# 📌 ملخص الملفات المرتبطة

## ✅ الملفات المستخرجة إلى هذا المجلد

هذا المجلد `upload_script` يحتوي على **جميع الملفات الأساسية** اللازمة لتشغيل سكريبت الرفع:

```
upload_script/
├── qdrant_upload.py      ⭐ السكريبت الأساسي
├── moaamlat.json         📊 بيانات المواد القانونية
├── requirements.txt      📦 المكتبات المطلوبة
├── setup.sh             🔧 سكريبت الإعداد
├── mcp_config.json      ⚙️ التكوين
├── README.md            📖 التعليمات
└── static/              🎨 ملفات الويب
    ├── index.html
    ├── script.js
    └── styles.css
```

## 🔗 الملفات الأخرى المتعلقة (في المجلد الأصلي)

تم **عدم نسخها** لأنها ليست ضرورية للسكريبت الأساسي:

| الملف | الدور | ملاحظات |
|------|-------|---------|
| `mcp_server.py` | خادم FastAPI | يوفر واجهة ويب/API (تطبيق منفصل) |
| `mcp_stdio_server.py` | خادم MCP | للتكامل مع LMStudio (تطبيق منفصل) |
| `mcp_client.py` | عميل MCP | للاختبار فقط |
| `test_mcp.py` | اختبارات | ملفات اختبار |
| `test_stdio_mcp.py` | اختبارات | ملفات اختبار |
| `convert_to_json.py` | تحويل الصيغ | لتحويل CSV/TXT إلى JSON |
| `example_integration.py` | أمثلة | أمثلة للتكامل |
| `madah.py` | أداة مساعدة | أداة إضافية |
| `stary.py` | أداة مساعدة | أداة إضافية |
| `uploads/` | مجلد الحمل | ملفات مرفوعة من المستخدمين |
| `waqf/` | بيانات إضافية | بيانات وقف إضافية |
| ملفات TXT و CSV | بيانات خام | نسخ أصلية من البيانات |

## 🚀 كيفية البدء

### الطريقة السريعة:

```bash
cd upload_script
bash setup.sh
python qdrant_upload.py
```

### أو يدوياً:

```bash
cd upload_script
source /Users/maa/Downloads/madani/.venv/bin/activate
pip install -r requirements.txt
python qdrant_upload.py --collection moaamlat --batch 128
```

## 📌 ملاحظات مهمة

1. **البيئة الافتراضية** موجودة في:
   ```
   /Users/maa/Downloads/madani/.venv/
   ```

2. **Qdrant** يجب أن يكون يعمل على `http://127.0.0.1:6333`

3. **اختياري**: إذا أردت استخدام واجهة الويب:
   ```bash
   # في المجلد الأصلي:
   source /Users/maa/Downloads/madani/.venv/bin/activate
   uvicorn mcp_server:app --reload --port 8000
   ```

4. **التضمينات (Embeddings)** تُحمل تلقائياً الأولى مرة

---

**الآن لديك مجلد منفصل يحتوي على كل ما تحتاجه لتشغيل سكريبت الرفع! ✨**
