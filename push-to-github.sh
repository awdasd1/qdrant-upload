#!/bin/bash

# 📤 سكريبت رفع المشروع إلى GitHub
# Script to push project to GitHub

set -e

echo "🚀 بدء رفع المشروع إلى GitHub..."
echo "=========================================="
echo ""

# تحديد بيانات المستودع
GITHUB_USERNAME="awdasd1"
REPO_NAME="qdrant-upload"
REPO_URL="https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"

echo "📌 بيانات المستودع:"
echo "   اسم المستخدم: $GITHUB_USERNAME"
echo "   اسم المستودع: $REPO_NAME"
echo "   الرابط: $REPO_URL"
echo ""

# التحقق من وجود git
if ! command -v git &> /dev/null; then
    echo "❌ Git غير مثبت"
    exit 1
fi

echo "✅ Git مثبت"

# التحقق من أن المستودع مهيأ
if [ ! -d ".git" ]; then
    echo "❌ هذا ليس مستودع Git. تشغيل git init..."
    git init
    git config user.email "awdasd1@example.com"
    git config user.name "awdasd1"
fi

# إضافة الـ remote
echo ""
echo "⚙️  إضافة الـ remote..."

# إزالة الـ remote القديم إن وجد
git remote remove origin 2>/dev/null || true

# إضافة الـ remote الجديد
git remote add origin "$REPO_URL"

echo "✅ تم إضافة الـ remote"

# التحقق من الفرع الرئيسي
echo ""
echo "📋 التحقق من الفرع..."

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "   الفرع الحالي: $CURRENT_BRANCH"

# إذا كان الفرع main بالفعل، لا نحتاج إلى تغييره
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "   إعادة تسمية الفرع إلى main..."
    git branch -M main
fi

echo ""
echo "📤 جاهز للرفع!"
echo ""
echo "⚠️  قبل الرفع، تأكد من:"
echo "   1️⃣  أنك أنشأت المستودع على GitHub: https://github.com/new"
echo "   2️⃣  اسم المستودع: $REPO_NAME"
echo "   3️⃣  أنك لديك حق الوصول"
echo ""

read -p "هل تريد متابعة الرفع؟ (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ تم الإلغاء"
    exit 1
fi

echo ""
echo "🔄 جاري الرفع..."

# محاولة الرفع
if git push -u origin main; then
    echo ""
    echo "✅ تم الرفع بنجاح! 🎉"
    echo ""
    echo "📍 روابط مهمة:"
    echo "   المستودع: $REPO_URL"
    echo "   الملفات: $REPO_URL/tree/main"
    echo "   الإصدارات: $REPO_URL/releases"
    echo ""
    echo "🌐 الخطوة التالية: ربط مع Coolify"
    echo "   1. افتح Coolify"
    echo "   2. اختر 'New Application'"
    echo "   3. ربط المستودع: $GITHUB_USERNAME/$REPO_NAME"
    echo "   4. اختر Buildpack: Nixpacks"
    echo ""
else
    echo ""
    echo "❌ فشل الرفع"
    echo "   تحقق من:"
    echo "   - اتصال الإنترنت"
    echo "   - بيانات GitHub"
    echo "   - أن المستودع موجود على GitHub"
    echo ""
    echo "💡 جرب:"
    echo "   ssh -T git@github.com  # للتحقق من SSH"
    echo "   git remote -v          # لعرض الـ remotes"
    echo "   git push -v origin main # لعرض تفاصيل الخطأ"
    exit 1
fi
