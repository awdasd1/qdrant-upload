"""
Upload Moaamlat data to Qdrant with metadata.

Usage (recommended offline embeddings with sentence-transformers):

1. Start Qdrant (Docker):
   docker run -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant

2. Install deps in your venv:
   source .venv/bin/activate
   pip install qdrant-client sentence-transformers tqdm

3. Run the uploader:
   python qdrant_upload.py --collection moaamlat --batch 128

This script expects `moaamlat.json` in the same folder or a CSV file with columns
`id`, `content`, `part`, and `page` for book pages. It will create a collection
named by `--collection` and upload vectors with payload like:
{
  "pageContent": "...",
  "content": "...",
  "النص": "...",
  "metadata": {
    "المصدر": "نظام المعاملات المدنية",
    "رقم المادة رقما": 99,
    "رقم المادة كتابة": "المادة التاسعة والتسعون"
  }
}

For CSV book uploads, metadata will include `المصدر` as the book name,
`رقم المادة رقما` from `id`, `رقم الجزء` from `part`, and `رقم الصفحة` from `page`.

You can switch to OpenAI embeddings by replacing the embedding part.
"""

import csv
import json
import os
import re
import argparse
from pathlib import Path
from tqdm import tqdm
import unicodedata

# Qdrant client
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

# Embeddings (sentence-transformers)
from sentence_transformers import SentenceTransformer
import httpx
import time
import urllib.parse as urlparse


def remove_diacritics(text: str) -> str:
    """إزالة التشكيل (الحروف الإضافية مثل الفتحات والضمات والسكونات) من النص العربي"""
    if not isinstance(text, str):
        return str(text)
    # تطبيع النص وإزالة الحروف المركبة
    text = unicodedata.normalize('NFKD', text)
    # إزالة جميع علامات التشكيل العربية
    arabic_diacritics = re.compile(r'[\u064B-\u065F]')
    return arabic_diacritics.sub('', text)


def parse_text_to_articles(text: str, system_name: str):
    pattern = re.compile(r"^(المادة\s+(?:ال)?[^\n]+)$", re.MULTILINE)
    parts = pattern.split(text)
    articles = []
    for i in range(1, len(parts), 2):
        article_label = parts[i].strip()
        article_text = parts[i + 1].strip() if i + 1 < len(parts) else ""
        article_text = re.sub(r"\s+", " ", article_text)
        # إزالة التشكيل من النص والعنوان
        article_text = remove_diacritics(article_text)
        article_label = remove_diacritics(article_label)
        if len(article_text) > 10:
            articles.append({
                "رقم المادة رقما": len(articles) + 1,
                "رقم المادة كتابة": article_label,
                "نص المادة": article_text,
                "اسم النظام": system_name
            })
    return articles


def parse_csv_to_articles(path: Path, system_name: str):
    articles = []
    with path.open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row:
                continue
            content = row.get('content') or row.get('Content') or row.get('CONTENT') or ''
            if not content:
                continue
            record_id = row.get('id') or row.get('ID') or row.get('Id') or ''
            part = row.get('part') or row.get('Part') or row.get('PART') or ''
            page = row.get('page') or row.get('Page') or row.get('PAGE') or ''
            # إزالة التشكيل من المحتوى
            content = remove_diacritics(content)
            try:
                numeric_id = int(record_id)
            except Exception:
                numeric_id = None
            metadata = {
                "رقم المادة رقما": numeric_id if numeric_id is not None else record_id,
                "رقم الجزء": part,
                "رقم الصفحة": page,
                "رقم المادة كتابة": f"الجزء {part} صفحة {page}" if part or page else ''
            }
            articles.append({
                "نص المادة": content,
                "اسم النظام": system_name,
                **metadata
            })
    return articles


def load_data(path: Path, system_name: str = "نظام المعاملات المدنية"):
    if path.suffix.lower() == ".json":
        try:
            with path.open(encoding='utf-8') as f:
                data = json.load(f)
            # إزالة التشكيل من جميع النصوص في JSON
            data = [remove_diacritics_from_item(item) for item in data]
            return data
        except json.JSONDecodeError:
            # Allow text files that were named .json
            text = path.read_text(encoding='utf-8')
            return parse_text_to_articles(text, system_name)
    if path.suffix.lower() == ".csv":
        return parse_csv_to_articles(path, system_name)
    text = path.read_text(encoding='utf-8')
    return parse_text_to_articles(text, system_name)


def remove_diacritics_from_item(item):
    """إزالة التشكيل من جميع حقول النص في العنصر"""
    if isinstance(item, dict):
        return {k: remove_diacritics(v) if isinstance(v, str) else v for k, v in item.items()}
    elif isinstance(item, str):
        return remove_diacritics(item)
    else:
        return item


def make_payload(item, pid=None, source_type='txt'):
    # Determine human-readable article label
    article_label = item.get("رقم المادة كتابة") or item.get("رقم المادة") or item.get("part") or item.get("رقم الجزء") or ""

    # Determine numeric article id: prefer explicit field, else use provided pid
    numeric = 0
    if "رقم المادة رقما" in item:
        try:
            numeric = int(item.get("رقم المادة رقما", 0))
        except Exception:
            numeric = item.get("رقم المادة رقما", 0)
    elif "id" in item:
        try:
            numeric = int(item.get("id", 0))
        except Exception:
            numeric = item.get("id", 0)
    elif pid is not None:
        numeric = int(pid)

    text_content = item.get("نص المادة", "") or item.get("content", "")
    metadata = {
        "المصدر": item.get("اسم النظام", item.get("book_name", "نظام المعاملات المدنية")),
        "رقم المادة رقما": numeric,
        "رقم المادة كتابة": article_label,
        "رقم الجزء": item.get("رقم الجزء", item.get("part", "")),
        "رقم الصفحة": item.get("رقم الصفحة", item.get("page", ""))
    }

    # Adjust metadata fields according to source type
    if source_type == 'txt':
        # For plain text systems, remove book/page fields
        metadata.pop("رقم الجزء", None)
        metadata.pop("رقم الصفحة", None)
    elif source_type == 'csv':
        # For CSV/books, remove article-specific fields
        metadata.pop("رقم المادة رقما", None)
        metadata.pop("رقم المادة كتابة", None)

    payload = {
        "content": text_content,
        "metadata": metadata
    }
    return payload


def create_collection(client: QdrantClient, collection_name: str, vector_size: int, upload_mode: str = 'overwrite', distance_type: str = 'cosine'):
    # Map distance type string to Qdrant Distance enum
    distance_map = {
        'cosine': rest.Distance.COSINE,
        'dot': rest.Distance.DOT,
        'euclidean': rest.Distance.EUCLID,
        'manhattan': rest.Distance.MANHATTAN,
    }
    distance_metric = distance_map.get(distance_type.lower(), rest.Distance.COSINE)
    
    # Safe create: check existence, delete if exists (for overwrite mode), then create
    try:
        exists = False
        try:
            cols = client.get_collections()
            exists = any(c.name == collection_name for c in getattr(cols, 'collections', []))
        except Exception:
            exists = False

        # For 'append' mode: if collection exists, don't delete it; if it doesn't exist, create it
        # For 'overwrite' mode: delete if exists, then create
        if upload_mode == 'overwrite':
            if exists:
                try:
                    client.delete_collection(collection_name)
                except Exception as e:
                    print("Warning deleting existing collection:", e)
            client.create_collection(
                collection_name=collection_name,
                vectors_config=rest.VectorParams(size=vector_size, distance=distance_metric),
            )
        else:  # append mode
            if not exists:
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=rest.VectorParams(size=vector_size, distance=distance_metric),
                )
            # If exists, just continue without deleting
    except Exception as e:
        print("Warning creating collection:", e)


def get_embeddings_gemini(texts, model, api_key, timeout=60, wait_on_rate_limit=True, gemini_batch_size=10):
    """Special handler for Google Gemini API - requires individual requests per text batch
    
    Args:
        texts: list of texts to embed
        model: model name (e.g., gemini-embedding-2)
        api_key: Google API key
        timeout: request timeout in seconds
        wait_on_rate_limit: whether to wait and retry on rate limit
        gemini_batch_size: number of texts to send per request (default: 10, max: 100)
    """
    final_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    embeddings = []
    safe_texts = [str(t) if not isinstance(t, str) else t for t in texts]
    
    # Process in configurable batches (Gemini can handle up to 100 texts per request)
    # Default 10 is conservative, user can increase for faster processing
    try:
        batch_size_int = int(gemini_batch_size)
    except (ValueError, TypeError):
        batch_size_int = 10
    
    batch_size = min(batch_size_int, 100, len(safe_texts))  # Cap at 100
    print(f"[Gemini] Processing {len(safe_texts)} texts with batch_size={batch_size}")
    
    # Use longer timeout for API calls (some batches may be large)
    actual_timeout = max(timeout, 120)  # At least 2 minutes
    
    with httpx.Client(timeout=actual_timeout) as client:
        for batch_num, i in enumerate(range(0, len(safe_texts), batch_size)):
            batch_texts = safe_texts[i:i+batch_size]
            print(f"[Gemini] Batch {batch_num+1}: Processing {len(batch_texts)} texts (indices {i}-{i+len(batch_texts)-1})...")
            
            payload = {
                "model": f"models/{model}",
                "content": {
                    "parts": [
                        {"text": text}
                        for text in batch_texts
                    ]
                }
            }
            
            r = None
            retry_count = 0
            max_retries = 3
            
            while retry_count < max_retries:
                try:
                    r = client.post(final_url, json=payload, headers=headers)
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        raise RuntimeError(f"Gemini API request failed after {max_retries} attempts: {str(e)}")
                    print(f"⚠️  Request failed (attempt {retry_count}/{max_retries}): {str(e)}")
                    time.sleep(5 * retry_count)  # Exponential backoff
            
            # Handle rate limit
            if r.status_code == 429:
                if wait_on_rate_limit:
                    print(f"⚠️  Rate limit hit (429). Waiting 60 seconds before retry...")
                    time.sleep(60)
                    try:
                        r = client.post(final_url, json=payload, headers=headers)
                    except Exception as e:
                        raise RuntimeError(f"Embedding API rate limit retry failed: {str(e)}")
                    if r.status_code == 429:
                        raise RuntimeError(f"Embedding API still rate limited after retry")
                else:
                    raise RuntimeError(f"Embedding API rate limit (429)")
            
            if r.status_code != 200:
                try:
                    txt = r.text
                except Exception:
                    txt = '<no body>'
                raise RuntimeError(f"Embedding API error {r.status_code} on batch {batch_num}: {txt}")
            
            data = r.json()
            # Google Gemini returns:
            # - Single text: {"embedding": {"values": [...]}}
            # - Multiple texts: {"embeddings": [{"values": [...]}, {"values": [...]}, ...]}
            if "embedding" in data:
                # Single embedding in response
                embeddings.append(data["embedding"]["values"])
            elif "embeddings" in data:
                # Multiple embeddings - extend (not append!) to preserve all
                for emb in data["embeddings"]:
                    if isinstance(emb, dict) and "values" in emb:
                        embeddings.append(emb["values"])
                    elif isinstance(emb, list):
                        embeddings.append(emb)
                    else:
                        embeddings.append(emb)
            else:
                raise ValueError(f"Unexpected Gemini response format: {data}")
    
    return embeddings


def make_qdrant_client(url: str, headers: dict | None = None):
    parsed = urlparse.urlparse(url)
    if parsed.scheme in ('http', 'https') and parsed.hostname:
        host = parsed.hostname
        https = parsed.scheme == 'https'
        port = parsed.port or (443 if https else 80)
        kwargs = {'host': host, 'https': https, 'port': port}
        if headers:
            kwargs['headers'] = headers
        if parsed.path and parsed.path != '/':
            kwargs['prefix'] = parsed.path.lstrip('/')
        return QdrantClient(**kwargs)
    return QdrantClient(url=url, headers=headers)


def get_embeddings_api(texts, api_url, model, api_key, cohere_input_type='classification', timeout=60, rate_limit_tokens=100000, wait_on_rate_limit=True, gemini_batch_size=10):
    # Special handling for Google Gemini (doesn't support batch in single request)
    if "generativelanguage.googleapis.com" in api_url or "gemini" in model.lower():
        return get_embeddings_gemini(texts, model, api_key, timeout, wait_on_rate_limit, gemini_batch_size)
    
    # Normalize API URL and add API key if needed
    final_url = api_url
    headers = {"Content-Type": "application/json"}
    
    # Determine API-specific constraints
    api_batch_limit = 1000  # Default large batch size
    if "cohere.com" in api_url:
        api_batch_limit = 96  # Cohere max 96 texts per request
    elif "jina.ai" in api_url:
        api_batch_limit = 2048  # Jina supports large batches
    elif "openai.com" in api_url:
        api_batch_limit = 2048  # OpenAI supports large batches
    
    print(f"[API] Processing {len(texts)} texts with API limit {api_batch_limit} per request")
    
    # Process in API-specific batches
    all_embeddings = []
    
    with httpx.Client(timeout=timeout) as client:
        for batch_start in range(0, len(texts), api_batch_limit):
            batch_end = min(batch_start + api_batch_limit, len(texts))
            batch_texts = texts[batch_start:batch_end]
            
            print(f"[API] Sub-batch {batch_start//api_batch_limit + 1}: Processing texts {batch_start}-{batch_end-1}")
            
            # Build provider-specific payloads
            if "cohere.com" in api_url:
                headers["Authorization"] = f"Bearer {api_key}"
                # Cohere enforces token limits per text; truncate long texts client-side.
                MAX_CHARS = 500
                safe_texts = []
                for t in batch_texts:
                    if not isinstance(t, str):
                        t = str(t)
                    if len(t) > MAX_CHARS:
                        t = t[:MAX_CHARS]
                    safe_texts.append(t)
                payload = {"model": model, "texts": safe_texts, "input_type": cohere_input_type, "truncate": "NONE"}
            
            elif "jina.ai" in api_url:
                headers["Authorization"] = f"Bearer {api_key}"
                # Jina has rate limits; don't truncate by default
                safe_texts = [str(t) if not isinstance(t, str) else t for t in batch_texts]
                payload = {"model": model, "input": safe_texts}
            
            elif "openai.com" in api_url:
                headers["Authorization"] = f"Bearer {api_key}"
                safe_texts = [str(t) if not isinstance(t, str) else t for t in batch_texts]
                payload = {"model": model, "input": safe_texts}
            
            else:
                # Default: try Bearer token
                headers["Authorization"] = f"Bearer {api_key}"
                safe_texts = [str(t) if not isinstance(t, str) else t for t in batch_texts]
                payload = {"model": model, "input": safe_texts}
            
            r = client.post(final_url, json=payload, headers=headers)
            
            # Handle rate limit error (429)
            if r.status_code == 429:
                try:
                    error_data = r.json()
                    detail = error_data.get('detail', '')
                except Exception:
                    detail = r.text
                
                if wait_on_rate_limit:
                    print(f"⚠️  Rate limit hit (429). Waiting 60 seconds before retry...")
                    print(f"Details: {detail}")
                    time.sleep(60)
                    # Retry once after waiting
                    r = client.post(final_url, json=payload, headers=headers)
                    if r.status_code == 429:
                        raise RuntimeError(f"Embedding API still rate limited after retry: {detail}")
                else:
                    raise RuntimeError(f"Embedding API rate limit (429): {detail}")
            
            # provide more helpful debug info on failures
            if r.status_code != 200:
                try:
                    txt = r.text
                except Exception:
                    txt = '<no body>'
                raise RuntimeError(f"Embedding API error {r.status_code} on sub-batch {batch_start//api_batch_limit + 1}: {txt}")
            
            data = r.json()
            # Try to extract embeddings from common shapes
            if isinstance(data, dict):
                # Google Gemini format: {"embeddings": [{"values": [...]}]}
                if "embeddings" in data and isinstance(data["embeddings"], list):
                    emb = []
                    for item in data["embeddings"]:
                        if "values" in item:
                            emb.append(item["values"])
                        elif "embedding" in item:
                            emb.append(item["embedding"])
                    all_embeddings.extend(emb if emb else data["embeddings"])
                
                # OpenAI/Cohere format: {"data": [{embedding: [...]}]}
                elif "data" in data and isinstance(data["data"], list):
                    emb = []
                    for item in data["data"]:
                        if "embedding" in item:
                            emb.append(item["embedding"])
                        elif "vector" in item:
                            emb.append(item["vector"])
                    all_embeddings.extend(emb)
                else:
                    raise ValueError(f"Unexpected API response format: {data}")
            
            # Fallback: expect list of vectors
            elif isinstance(data, list):
                all_embeddings.extend(data)
            else:
                raise ValueError(f"Unknown embedding API response format: {data}")
    
    print(f"[API] ✓ Completed! Total embeddings: {len(all_embeddings)}")
    return all_embeddings


def ping_qdrant(url: str, api_key: str | None = None, timeout: int = 5):
    """Try several URL variants to detect reachable Qdrant endpoint.

    Returns (ok: bool, info: status_code or error message, tried_list)
    """
    candidates = []
    parsed = urlparse.urlparse(url)
    base = url.rstrip('/')
    candidates.append(base)

    # If port explicitly 6333, also try without port (cloud often uses 443)
    if parsed.port == 6333:
        host_only = f"{parsed.scheme}://{parsed.hostname}"
        if host_only not in candidates:
            candidates.append(host_only)

    # If https, also try http variant
    if parsed.scheme == 'https':
        http_variant = url.replace('https://', 'http://')
        if http_variant not in candidates:
            candidates.append(http_variant.rstrip('/'))

    header_sets = [{}]
    if api_key:
        header_sets = [
            {'x-api-key': api_key},
            {'Authorization': f'Bearer {api_key}'}
        ]

    last_err = None
    tried = []
    for candidate in candidates:
        test_url = candidate.rstrip('/') + '/collections'
        tried.append(test_url)
        best_status = None
        best_headers = None
        for headers in header_sets:
            for attempt in range(3):
                try:
                    r = httpx.get(test_url, headers=headers, timeout=timeout)
                    if r.status_code == 200:
                        return True, r.status_code, candidate, tried, headers
                    if r.status_code in (401, 403) and best_status not in (200, 401, 403):
                        best_status = r.status_code
                        best_headers = headers
                    break
                except Exception as e:
                    last_err = str(e)
                    time.sleep(1)
        if best_headers is not None:
            return True, best_status, candidate, tried, best_headers
    return False, last_err, None, tried, None


def upload(args):
    script_dir = Path(__file__).parent
    data_path = Path(args.input_file) if args.input_file else script_dir / "moaamlat.json"
    if not data_path.exists():
        raise FileNotFoundError(f"Input file not found: {data_path}")

    data = load_data(data_path, system_name=args.system_name)
    print(f"Loaded {len(data)} records from {data_path}")

    # Determine source type for payload field adjustments
    suffix = data_path.suffix.lower()
    if suffix == '.csv':
        source_type = 'csv'
    else:
        source_type = 'txt'

    # choose embedding source
    use_api = bool(args.embed_api_url)
    api_key = args.embed_api_key or os.environ.get("EMBED_API_KEY")

    if use_api and not api_key:
        raise ValueError("EMBED_API_KEY environment variable not set for API embedding mode. Please provide your Cohere API key in the web form or set it as an environment variable before running the server.")

    if not use_api:
        model = SentenceTransformer(args.model)
        vector_size = model.get_sentence_embedding_dimension()
        print("Using local embedding model:", args.model, "dim=", vector_size)
    else:
        vector_size = args.vector_size or 1024
        print("Using external embedding API:", args.embed_api_url, "model=", args.model, "dim=", vector_size)

    # Qdrant client
    qdrant_api_key = args.qdrant_api_key or os.environ.get("QDRANT_API_KEY")
    ok, info, qdrant_url, tried, auth_headers = ping_qdrant(args.qdrant_url, api_key=qdrant_api_key)
    if not ok:
        raise ConnectionError(
            f"Cannot reach Qdrant at {args.qdrant_url}: {info}\nTried: {tried}\n"
            f"Check the URL, network, or cloud access and ensure the service is reachable.")

    chosen_url = qdrant_url or args.qdrant_url
    if chosen_url != args.qdrant_url:
        print(f"Using detected Qdrant URL: {chosen_url} instead of {args.qdrant_url}")
    if auth_headers:
        print(f"Using detected auth headers for Qdrant: {list(auth_headers.keys())}")

    client = make_qdrant_client(chosen_url, headers=auth_headers)

    create_collection(client, args.collection, vector_size, upload_mode=args.upload_mode, distance_type=args.distance_type)

    batch_texts = []
    ids = []
    payloads = []

    for i, item in enumerate(tqdm(data, desc="Preparing")):
        txt = item.get("نص المادة", "")
        payload = make_payload(item, pid=i + 1, source_type=source_type)
        batch_texts.append(txt)
        ids.append(i + 1)  # 1-based id
        payloads.append(payload)

        if len(batch_texts) >= args.batch:
            if use_api:
                vectors = get_embeddings_api(batch_texts, args.embed_api_url, args.model, api_key, cohere_input_type=args.cohere_input_type, rate_limit_tokens=args.batch_tokens_limit, wait_on_rate_limit=args.wait_on_rate_limit, gemini_batch_size=args.gemini_batch_size)
            else:
                vectors = model.encode(batch_texts, show_progress_bar=False, convert_to_numpy=True)

            # Split large batches into smaller Qdrant chunks (max 500 points per upsert to avoid 32MB payload limit)
            qdrant_chunk_size = 500
            for chunk_start in range(0, len(vectors), qdrant_chunk_size):
                chunk_end = min(chunk_start + qdrant_chunk_size, len(vectors))
                points = []
                for j in range(chunk_start, chunk_end):
                    vec = vectors[j]
                    vec_list = vec.tolist() if hasattr(vec, 'tolist') else list(vec)
                    points.append(rest.PointStruct(id=ids[j], vector=vec_list, payload=payloads[j]))
                print(f"[Qdrant] Upserting chunk {chunk_start//qdrant_chunk_size + 1}: {len(points)} points...")
                client.upsert(collection_name=args.collection, points=points)
            
            batch_texts, ids, payloads = [], [], []

    # final batch
    if batch_texts:
        if use_api:
            vectors = get_embeddings_api(batch_texts, args.embed_api_url, args.model, api_key, cohere_input_type=args.cohere_input_type, rate_limit_tokens=args.batch_tokens_limit, wait_on_rate_limit=args.wait_on_rate_limit, gemini_batch_size=args.gemini_batch_size)
        else:
            vectors = model.encode(batch_texts, show_progress_bar=False, convert_to_numpy=True)

        # Split large batches into smaller Qdrant chunks (max 500 points per upsert to avoid 32MB payload limit)
        qdrant_chunk_size = 500
        for chunk_start in range(0, len(vectors), qdrant_chunk_size):
            chunk_end = min(chunk_start + qdrant_chunk_size, len(vectors))
            points = []
            for j in range(chunk_start, chunk_end):
                vec = vectors[j]
                vec_list = vec.tolist() if hasattr(vec, 'tolist') else list(vec)
                points.append(rest.PointStruct(id=ids[j], vector=vec_list, payload=payloads[j]))
            print(f"[Qdrant] Upserting final chunk {chunk_start//qdrant_chunk_size + 1}: {len(points)} points...")
            client.upsert(collection_name=args.collection, points=points)

    print("Upload complete")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--collection', type=str, default='moaamlat')
    parser.add_argument('--qdrant-url', type=str, default='http://127.0.0.1:6333')
    parser.add_argument('--qdrant-api-key', type=str, default='', help='Qdrant API key for cloud collections')
    parser.add_argument('--batch', type=int, default=3000, help='Batch size for processing records (default: 3000). This controls how many texts are processed together for ALL embedding providers')
    parser.add_argument('--batch-tokens-limit', type=int, default=100000, help='Maximum tokens per batch for APIs with rate limits (default: 100000 for Jina)')
    parser.add_argument('--wait-on-rate-limit', type=bool, default=True, help='Wait and retry on rate limit errors (429)')
    parser.add_argument('--gemini-batch-size', type=int, default=10, help='[DEPRECATED] For Google Gemini only: number of texts per API request (default: 10, max: 100). Use --batch instead for all providers')
    parser.add_argument('--input-file', type=str, default='', help='Optional input file path (JSON or TXT)')
    parser.add_argument('--system-name', type=str, default='نظام المعاملات المدنية', help='System name to use for text uploads or missing metadata')
    parser.add_argument('--model', type=str, default='all-MiniLM-L6-v2', help='sentence-transformers model')
    parser.add_argument('--embed-api-url', type=str, default='', help='External embedding API URL (e.g., https://api.cohere.com/v1/embed)')
    parser.add_argument('--embed-api-key', type=str, default='', help='Embedding provider API key (Cohere)')
    parser.add_argument('--vector-size', type=int, default=1024, help='Vector size for external embeddings')
    parser.add_argument('--upload-mode', type=str, default='overwrite', choices=['overwrite', 'append'], help='Upload mode: overwrite (delete and recreate) or append (add to existing collection)')
    parser.add_argument('--distance-type', type=str, default='cosine', choices=['cosine', 'dot', 'euclidean', 'manhattan'], help='Distance metric for vector similarity: cosine (default), dot, euclidean, or manhattan')
    parser.add_argument('--cohere-input-type', type=str, default='classification', choices=['search_document', 'search_query', 'classification', 'clustering'], help='Input type for Cohere embeddings (search_document, search_query, classification, clustering)')
    args = parser.parse_args()
    upload(args)
