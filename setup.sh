#!/bin/bash

# سكريبت إعداد وتشغيل سكريبت الرفع

set -e  # توقف على أي خطأ

echo "🔧 إعداد سكريبت رفع البيانات..."
echo ""

# تفعيل البيئة الافتراضية
VENV_PATH="/Users/maa/Downloads/madani/.venv"
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ البيئة الافتراضية غير موجودة في: $VENV_PATH"
    exit 1
fi

source "$VENV_PATH/bin/activate"
echo "✅ تفعيل البيئة الافتراضية"

# التحقق من المكتبات
echo "📦 التحقق من المكتبات المطلوبة..."

# تثبيت المكتبات من requirements.txt
pip install -q -r requirements.txt

# تثبيت المكتبات الإضافية
echo "   تثبيت sentence-transformers..."
pip install -q sentence-transformers

echo "   تثبيت qdrant-client..."
pip install -q qdrant-client

echo "✅ جميع المكتبات مثبتة"
echo ""

# التحقق من Qdrant
echo "🔍 التحقق من اتصال Qdrant..."
QDRANT_URL="http://127.0.0.1:6333"

if curl -s "$QDRANT_URL/collections" > /dev/null 2>&1; then
    echo "✅ Qdrant متصل على: $QDRANT_URL"
else
    echo "⚠️  Qdrant غير متصل. تأكد من تشغيل:"
    echo "   docker run -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant"
    echo ""
fi

# عرض خيارات التشغيل
echo "🚀 خيارات التشغيل:"
echo ""
echo "1️⃣  الأمر الأساسي (الافتراضي):"
echo "   python qdrant_upload.py"
echo ""
echo "2️⃣  مع تحديد المجموعة والدفعة:"
echo "   python qdrant_upload.py --collection moaamlat --batch 128"
echo ""
echo "3️⃣  مع API للتضمينات (Cohere):"
echo "   EMBED_API_KEY=your-key python qdrant_upload.py --embed-api-url 'https://api.cohere.com/v1/embed' --model 'embed-english-light-v3.0'"
echo ""
echo "4️⃣  مع ملف إدخال مخصص:"
echo "   python qdrant_upload.py --input-file path/to/file.json"
echo ""
echo "📝 لعرض جميع الخيارات:"
echo "   python qdrant_upload.py --help"
echo ""
