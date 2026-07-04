from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
from typing import List
import shutil
import subprocess
import sys
import os
import re
import uuid
from datetime import datetime

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional dependency in some environments
    SentenceTransformer = None

try:
    from qdrant_client import QdrantClient
except Exception:  # pragma: no cover - optional dependency in some environments
    QdrantClient = None

app = FastAPI(title="MoAamlat MCP Server", version="0.1")

# Initialize embedding model and Qdrant client (lazy loaded)
_embedding_model = None
_qdrant_client = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        if SentenceTransformer is None:
            print("Warning: sentence-transformers is not installed; local embeddings are unavailable")
            return None
        try:
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"Warning: failed to load embedding model: {e}")
    return _embedding_model


def get_qdrant_client():
    global _qdrant_client
    if _qdrant_client is None:
        if QdrantClient is None:
            print("Warning: qdrant-client is not installed; Qdrant search is unavailable")
            return None
        try:
            qdrant_url = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
            qdrant_api_key = os.getenv("QDRANT_API_KEY", "")
            if qdrant_api_key:
                _qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
            else:
                _qdrant_client = QdrantClient(url=qdrant_url)
        except Exception as e:
            print(f"Warning: failed to connect to Qdrant: {e}")
    return _qdrant_client


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "moaamlat.json"
if not DATA_PATH.exists():
    raise FileNotFoundError(f"Data file not found: {DATA_PATH}")


def parse_plain_text_to_articles(text: str) -> List[dict]:
    articles = []
    pattern = re.compile(r"(المادة\s+[^\n]+)\n(.*?)(?=(?:\nالمادة\s+[^\n]+\n)|\Z)", re.S)
    for match in pattern.finditer(text):
        heading = match.group(1).strip()
        body = match.group(2).strip()
        articles.append({"رقم المادة": heading, "نص المادة": body})
    if articles:
        return articles
    return [{"رقم المادة": "1", "نص المادة": text.strip()}]


def load_data(path: Path) -> List[dict]:
    content = path.read_text(encoding="utf-8")
    try:
        data = json.loads(content)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        return parse_plain_text_to_articles(content)


DATA = load_data(DATA_PATH)

UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
UPLOAD_JOBS = {}

STATIC_DIR = BASE_DIR / "static"
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(exist_ok=True)
    for filename in ["index.html", "script.js", "styles.css"]:
        src = BASE_DIR / filename
        if src.exists():
            shutil.copy2(src, STATIC_DIR / filename)


def normalize_query(q: str) -> str:
    return q.strip()

# Mount static files directory
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health", response_class=JSONResponse)
def health():
    return {"status": "ok"}


@app.get("/", response_class=RedirectResponse)
def root():
    return RedirectResponse(url="/admin/upload")


@app.get("/search", response_class=JSONResponse)
def search(q: str = Query(..., description="بحث نصي في رقم المادة أو نصها"), limit: int = Query(50, description="حد أقصى لعدد النتائج")):
    qn = normalize_query(q)
    results = []
    for item in DATA:
        if qn in item.get("رقم المادة", "") or qn in item.get("نص المادة", ""):
            results.append(item)
            if len(results) >= limit:
                break
    return {"query": q, "count": len(results), "results": results}


@app.get("/search_semantic", response_class=JSONResponse)
def search_semantic(
    q: str = Query(..., description="بحث شبهي (semantic) عن نصوص المواد"),
    collection: str = Query("moaamlat", description="اسم الكولكشن في Qdrant"),
    limit: int = Query(10, description="حد أقصى لعدد النتائج"),
    use_cohere: bool = Query(False, description="استخدم Cohere API بدل النموذج المحلي")
):
    """
    ابحث شبهياً عن نصوص المواد باستخدام Qdrant.
    يرجع pageContent و metadata من كل نتيجة.
    إذا كانت المجموعة dim=1024، استخدم use_cohere=true أو علّم EMBED_API_KEY.
    """
    try:
        client = get_qdrant_client()
        if client is None:
            raise HTTPException(status_code=503, detail="Qdrant client not available")
        
        # Determine which embedding method to use
        embed_api_key = os.environ.get("EMBED_API_KEY")
        if use_cohere or embed_api_key:
            # Use Cohere API
            if not embed_api_key:
                raise HTTPException(status_code=400, detail="EMBED_API_KEY not set but use_cohere=true")
            
            # Truncate query for Cohere
            query_text = q[:500] if len(q) > 500 else q
            headers = {"Authorization": f"Bearer {embed_api_key}", "Content-Type": "application/json"}
            payload = {"model": "embed-multilingual-v3.0", "texts": [query_text], "input_type": "classification", "truncate": "NONE"}
            
            import httpx
            with httpx.Client(timeout=60) as http_client:
                r = http_client.post("https://api.cohere.com/v1/embed", json=payload, headers=headers)
                if r.status_code != 200:
                    raise RuntimeError(f"Cohere API error {r.status_code}: {r.text}")
                data = r.json()
                embeddings = data.get("embeddings", [])
                if not embeddings:
                    raise RuntimeError("No embeddings returned from Cohere")
                query_embedding = embeddings[0]
        else:
            # Use local model
            model = get_embedding_model()
            if model is None:
                raise HTTPException(status_code=503, detail="Embedding model not available")
            query_embedding = model.encode(q).tolist()
        
        # Search in Qdrant using query_points
        search_result = client.query_points(
            collection_name=collection,
            query=query_embedding,
            limit=limit,
        ).points
        
        # Format results: include content and metadata from payload
        results = []
        for scored_point in search_result:
            payload = scored_point.payload or {}
            result = {
                "id": scored_point.id,
                "score": scored_point.score,
                "content": payload.get("content", ""),
                "metadata": payload.get("metadata", {})
            }
            results.append(result)
        
        return {
            "query": q,
            "collection": collection,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.get("/article/{article_id}", response_class=JSONResponse)
def get_article(article_id: str):
    aid = normalize_query(article_id)
    # exact match first
    for item in DATA:
        if item.get("رقم المادة", "") == aid:
            return item
    # partial match
    for item in DATA:
        if aid in item.get("رقم المادة", ""):
            return item
    # numeric match: allow querying by numeric index (1-based)
    if aid.isdigit():
        idx = int(aid) - 1
        if 0 <= idx < len(DATA):
            return DATA[idx]
    raise HTTPException(status_code=404, detail=f"Article not found: {article_id}")


@app.get("/admin/upload", response_class=HTMLResponse)
def upload_form():
    html = """
    <html>
      <head>
        <meta charset="utf-8" />
        <title>رفع نظام جديد إلى Qdrant</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 24px; direction: rtl; background: #f6f7fb; color: #111; }
          .card { max-width: 720px; margin: auto; padding: 24px; background: #fff; box-shadow: 0 16px 38px rgba(0,0,0,0.08); border-radius: 16px; }
          h1 { margin-top: 0; color: #1f2937; }
          label { display: block; margin: 16px 0 6px; font-weight: 700; }
          input[type=text], input[type=url], input[type=password], select, textarea { width: 100%; padding: 12px 14px; border: 1px solid #d1d5db; border-radius: 12px; box-sizing: border-box; }
          input[type=file] { width: 100%; }
          button { margin-top: 18px; padding: 12px 18px; border: none; border-radius: 12px; background: #2563eb; color: #fff; cursor: pointer; font-weight: 700; }
          button:disabled { opacity: 0.65; cursor: not-allowed; }
          .hint { font-size: 0.95rem; color: #4b5563; margin-top: 6px; }
          .status { margin: 18px 0; padding: 14px; border-radius: 12px; background: #eef2ff; color: #1e3a8a; display: none; }
          .status.error { background: #fee2e2; color: #991b1b; }
          .status.success { background: #dcfce7; color: #166534; }
          .loader { display: inline-block; width: 20px; height: 20px; border: 3px solid #c7d2fe; border-top: 3px solid #2563eb; border-radius: 50%; animation: spin 1s linear infinite; vertical-align: middle; margin-left: 10px; }
          @keyframes spin { to { transform: rotate(360deg); } }
          .footer { font-size: 0.9rem; color: #6b7280; margin-top: 16px; }
        </style>
      </head>
      <body>
        <div class="card">
          <h1>رفع نظام جديد إلى Qdrant</h1>
          <p class="hint">اختر ملف JSON أو TXT أو CSV (لدعم كتب الفقهية)، ثم أدخل اسم الكتاب أو النظام واسم الكولكشن. يمكن تغيير عنوان Qdrant وAPI Key للكلاود.</p>
          <form id="uploadForm">
            <label>ملف النظام أو الكتاب (JSON أو TXT أو CSV)</label>
            <input id="fileInput" name="file" type="file" accept="application/json,text/plain,text/csv" required />

            <label>اسم النظام</label>
            <input id="systemName" name="system_name" type="text" placeholder="مثال: نظام الإثبات" required />

            <label>اسم الكولكشن في Qdrant</label>
            <input id="collectionName" name="collection" type="text" placeholder="مثال: ithbat" value="moaamlat" required />

            <label>خيار الرفع</label>
            <select id="uploadMode" name="upload_mode" required>
              <option value="overwrite">كتابة فوق (استبدال المجموعة)</option>
              <option value="append">إضافة (إضافة إلى المجموعة الموجودة)</option>
            </select>

            <label>مصدر التضمين</label>
            <select id="embeddingSource" name="embedding_source" required onchange="toggleEmbeddingFields()">
              <option value="local">محلي (HuggingFace - مجاني)</option>
              <option value="api">خارجي (OpenAI / Cohere / مخصص)</option>
            </select>
            <p class="hint">اختر محلي للتضمين المجاني أو خارجي لاستخدام OpenAI/Cohere/API مخصص</p>

            <div id="localEmbeddingFields" style="display: block;">
              <label>اسم نموذج HuggingFace</label>
              <input id="localModelName" name="local_model_name" type="text" placeholder="مثال: all-MiniLM-L6-v2" value="all-MiniLM-L6-v2" />
              <p class="hint">نماذج موصى بها: all-MiniLM-L6-v2 (dim=384)، multilingual-e5-base (dim=768)</p>
            </div>

            <div id="apiEmbeddingFields" style="display: none;">
              <label>اسم نموذج التضمين</label>
              <input id="apiModelName" name="api_model_name" type="text" placeholder="مثال: embed-multilingual-v3.0 أو text-embedding-3-large" required />
              <p class="hint">أدخل اسم النموذج الدقيق من مزود الخدمة</p>

              <label>URL خادم التضمين (API)</label>
              <input id="embedApiUrl" name="embed_api_url" type="url" placeholder="مثال: https://api.cohere.com/v1/embed أو https://api.openai.com/v1/embeddings" required />
              <p class="hint">أمثلة:
                <ul style="margin: 6px 0;">
                  <li>Cohere: https://api.cohere.com/v1/embed</li>
                  <li>OpenAI: https://api.openai.com/v1/embeddings</li>
                  <li>Google Gemini: https://generativelanguage.googleapis.com (سيتم إضافة الـ endpoint تلقائياً)</li>
                  <li>Jina: https://api.jina.ai/v1/embeddings</li>
                </ul>
              </p>

              <label>نوع الإدخال (Cohere Input Type)</label>
              <select id="cohereInputType" name="cohere_input_type">
                <option value="search_document">search_document - للمستندات المخزنة في قاعدة البيانات</option>
                <option value="search_query">search_query - لاستعلامات البحث</option>
                <option value="classification">classification - للتصنيف (افتراضي)</option>
                <option value="clustering">clustering - للتجميع</option>
              </select>
              <p class="hint">اختر "search_document" لتخزين المستندات أو "search_query" للبحث عنها</p>
            </div>

            <label>حجم التضمين (Vector Dimension)</label>
            <input id="vectorSize" name="vector_size" type="number" placeholder="1024" value="1024" min="1" max="4096" required />
            <p class="hint">حجم المتجه المتوقع من النموذج (مثال: 384, 768, 1024, 1536, 3072, 4096)</p>

            <label>نوع المسافة (Distance Type)</label>
            <select id="distanceType" name="distance_type" required>
              <option value="cosine">Cosine (جيب التمام) - موصى به</option>
              <option value="dot">Dot Product (الضرب النقطي)</option>
              <option value="euclidean">Euclidean (المسافة الإقليدية)</option>
              <option value="manhattan">Manhattan (مسافة مانهاتن)</option>
            </select>
            <p class="hint">Cosine: للمقارنة بين الاتجاهات | Dot: للقيم الموحدة | Euclidean/Manhattan: للمسافات الهندسية</p>

            <label>حجم الدفعة الرئيسي (Batch Size) - جميع أنواع التضمين</label>
            <input id="batchSize" name="batch_size" type="number" placeholder="3000" value="3000" min="1" max="10000" required />
            <p class="hint">عدد النصوص المعالجة معاً في كل دفعة (افتراضي: 3000). زيادة هذا يسرع معالجة الملفات الكبيرة! استخدم 3000-5000 للملفات الضخمة.</p>

            <label>حجم دفعة Google Gemini (Gemini Batch Size) - Gemini فقط</label>
            <input id="geminiBatchSize" name="gemini_batch_size" type="number" placeholder="10" value="10" min="1" max="100" />
            <p class="hint">عدد النصوص المرسلة في كل request API لـ Google Gemini (افتراضي: 10، الأقصى: 100). يُستخدم فقط عند اختيار Gemini. جرب 50-100 للسرعة.</p>

            <label>عنوان Qdrant</label>
            <input id="qdrantUrl" name="qdrant_url" type="url" placeholder="http://127.0.0.1:6333" value="http://127.0.0.1:6333" required />

            <label>Qdrant API Key (اختياري)</label>
            <input id="qdrantApiKey" name="qdrant_api_key" type="password" placeholder="API Key للكلاود" />

            <label>Embed API Key (اختياري)</label>
            <input id="embedApiKey" name="embed_api_key" type="password" placeholder="مفتاح Cohere او وصول خارجي" />
            <p class="hint">إذا كنت تستخدم Cohere، أدخل مفتاح EMBED_API_KEY هنا.</p>

            <button id="submitButton" type="submit">بدء الرفع</button>
          </form>

          <div id="status" class="status"></div>
          <div id="logLink" class="footer"></div>
        </div>

        <script>
          const form = document.getElementById('uploadForm');
          const statusBox = document.getElementById('status');
          const submitButton = document.getElementById('submitButton');
          const logLink = document.getElementById('logLink');

          function toggleEmbeddingFields() {
            const source = document.getElementById('embeddingSource').value;
            const localFields = document.getElementById('localEmbeddingFields');
            const apiFields = document.getElementById('apiEmbeddingFields');
            
            if (source === 'local') {
              localFields.style.display = 'block';
              apiFields.style.display = 'none';
              document.getElementById('apiModelName').removeAttribute('required');
              document.getElementById('embedApiUrl').removeAttribute('required');
            } else {
              localFields.style.display = 'none';
              apiFields.style.display = 'block';
              document.getElementById('apiModelName').setAttribute('required', 'required');
              document.getElementById('embedApiUrl').setAttribute('required', 'required');
            }
          }

          async function pollStatus(jobId) {
            while (true) {
              const r = await fetch(`/admin/upload/status/${jobId}`);
              const data = await r.json();
              if (data.status === 'running' || data.status === 'pending') {
                statusBox.style.display = 'block';
                statusBox.className = 'status';
                statusBox.innerHTML = `<span class="loader"></span> جاري التنفيذ...`;
                await new Promise(resolve => setTimeout(resolve, 2000));
                continue;
              }
              if (data.status === 'success') {
                statusBox.style.display = 'block';
                statusBox.className = 'status success';
                statusBox.textContent = 'تم الرفع بنجاح! تم إنشاء الكولكشن: ' + data.collection;
                logLink.innerHTML = `<a href="/admin/upload/log/${jobId}" target="_blank">عرض سجل التحميل</a>`;
              } else {
                statusBox.style.display = 'block';
                statusBox.className = 'status error';
                statusBox.textContent = 'فشل الرفع: ' + (data.error || 'حدث خطأ غير متوقع');
                logLink.innerHTML = `<a href="/admin/upload/log/${jobId}" target="_blank">عرض سجل الخطأ</a>`;
              }
              submitButton.disabled = false;
              break;
            }
          }

          form.addEventListener('submit', async (event) => {
            event.preventDefault();
            submitButton.disabled = true;
            statusBox.style.display = 'block';
            statusBox.className = 'status';
            statusBox.innerHTML = `<span class="loader"></span> إرسال الملف وبدء العملية...`;
            logLink.textContent = '';

            const formData = new FormData(form);
            const response = await fetch('/admin/upload', {
              method: 'POST',
              body: formData,
            });
            if (!response.ok) {
              const error = await response.text();
              statusBox.className = 'status error';
              statusBox.textContent = 'خطأ في الإرسال: ' + error;
              submitButton.disabled = false;
              return;
            }
            const data = await response.json();
            if (data.job_id) {
              pollStatus(data.job_id);
            } else {
              statusBox.className = 'status error';
              statusBox.textContent = 'لم يتم الحصول على رقم المهمة.';
              submitButton.disabled = false;
            }
          });
        </script>
      </body>
    </html>
    """
    return HTMLResponse(content=html)


def set_job_status(job_id: str, status: str, error: str = '', message: str = ''):
    job = UPLOAD_JOBS.get(job_id)
    if job:
        job['status'] = status
        job['error'] = error
        job['message'] = message
        if status in ['success', 'failure']:
            job['finished_at'] = datetime.utcnow().isoformat() + 'Z'


def _run_uploader_script(job_id: str, upload_path: Path, collection: str, system_name: str, qdrant_url: str, qdrant_api_key: str, embed_api_key: str, log_path: Path, upload_mode: str = 'overwrite', embedding_source: str = 'local', local_model_name: str = 'all-MiniLM-L6-v2', api_model_name: str = '', embed_api_url: str = '', vector_size: str = '1024', distance_type: str = 'cosine', cohere_input_type: str = 'classification', batch_size: str = '3000', gemini_batch_size: str = '10'):
    set_job_status(job_id, 'running')
    env = os.environ.copy()
    if qdrant_api_key:
        env['QDRANT_API_KEY'] = qdrant_api_key
    if embed_api_key:
        env['EMBED_API_KEY'] = embed_api_key
    
    # Determine model and API URL based on embedding source
    if embedding_source == 'local':
        model_name = local_model_name
        api_url = ''  # empty = use local embeddings
    else:  # api
        model_name = api_model_name
        api_url = embed_api_url
    
    cmd = [
        sys.executable,
        str(Path(__file__).parent / 'qdrant_upload.py'),
        '--collection', collection,
        '--input-file', str(upload_path),
        '--system-name', system_name,
        '--qdrant-url', qdrant_url,
        '--qdrant-api-key', qdrant_api_key,
        '--embed-api-url', api_url,
        '--embed-api-key', embed_api_key,
        '--model', model_name,
        '--vector-size', vector_size,
        '--batch', batch_size,
        '--upload-mode', upload_mode,
        '--distance-type', distance_type,
        '--cohere-input-type', cohere_input_type,
        '--gemini-batch-size', gemini_batch_size
    ]
    with open(log_path, 'w', encoding='utf-8') as logf:
        proc = subprocess.run(cmd, env=env, cwd=str(Path(__file__).parent), stdout=logf, stderr=logf)
    if proc.returncode == 0:
        set_job_status(job_id, 'success', message='Upload completed successfully')
    else:
        set_job_status(job_id, 'failure', error=f'Exit code {proc.returncode}')


@app.post("/admin/upload", response_class=JSONResponse)
def handle_upload(background_tasks: BackgroundTasks, file: UploadFile = File(...), system_name: str = Form(...), collection: str = Form(...), qdrant_url: str = Form(...), qdrant_api_key: str = Form(''), embed_api_key: str = Form(''), upload_mode: str = Form('overwrite'), embedding_source: str = Form('local'), local_model_name: str = Form('all-MiniLM-L6-v2'), api_model_name: str = Form(''), embed_api_url: str = Form(''), vector_size: str = Form('1024'), distance_type: str = Form('cosine'), cohere_input_type: str = Form('classification'), batch_size: str = Form('3000'), gemini_batch_size: str = Form('10')):
    upload_id = str(uuid.uuid4())
    uploads_dir = UPLOADS_DIR
    extension = Path(file.filename).suffix.lower() if file.filename else '.json'
    if extension not in ['.json', '.txt', '.csv']:
        extension = '.json'
    upload_path = uploads_dir / f"upload_{collection}_{upload_id}{extension}"
    with upload_path.open('wb') as out:
        shutil.copyfileobj(file.file, out)

    log_path = uploads_dir / f"upload_{collection}_{upload_id}.log"
    UPLOAD_JOBS[upload_id] = {
        'id': upload_id,
        'status': 'pending',
        'collection': collection,
        'file': str(upload_path),
        'log': str(log_path),
        'error': '',
        'message': '',
        'created_at': str(Path().absolute()),
        'finished_at': '',
    }
    background_tasks.add_task(_run_uploader_script, upload_id, upload_path, collection, system_name, qdrant_url, qdrant_api_key, embed_api_key, log_path, upload_mode, embedding_source, local_model_name, api_model_name, embed_api_url, vector_size, distance_type, cohere_input_type, batch_size, gemini_batch_size)
    return {'status': 'started', 'job_id': upload_id, 'collection': collection, 'log': str(log_path)}


@app.get('/admin/upload/status/{job_id}', response_class=JSONResponse)
def upload_status(job_id: str):
    job = UPLOAD_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    return job


@app.get('/admin/upload/log/{job_id}', response_class=HTMLResponse)
def upload_log(job_id: str):
    job = UPLOAD_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    log_path = Path(job['log'])
    if not log_path.exists():
        raise HTTPException(status_code=404, detail='Log file not found')
    text = log_path.read_text(encoding='utf-8', errors='replace')
    return HTMLResponse(f"<pre style='white-space: pre-wrap; word-wrap: break-word; font-family: monospace;'>" + text + "</pre>")
