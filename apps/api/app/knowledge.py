"""Knowledge Spaces: chunking, embeddings, hybrid retrieval, ingestion from text, files, URLs, datasets and repositories.

Vectors are stored as JSON on each chunk and compared with numpy. That is exact and fast enough for a pilot corpus
(tens of thousands of chunks); on Postgres the same table maps onto pgvector without changing callers.
Every embedding call is metered on the ledger as feature "knowledge".
"""

from __future__ import annotations

import base64
import hashlib
import html
import io
import itertools
import math
import re
import threading
import time
import zipfile
from collections import Counter

import httpx
import numpy as np
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KnowledgeChunk, KnowledgeDocument, KnowledgeSpace, UsageEvent, User

EMBEDDING_MODELS: dict[str, dict] = {
    "local-hash": {"name": "Local hashed n-grams", "provider": "Playground", "dims": 384, "price_per_m": 0.0, "env": None, "litellm": None, "note": "No network, no cost. Lexical semantics via hashed unigrams and bigrams. Good for pilots and tests."},
    "text-embedding-3-small": {"name": "OpenAI text-embedding-3-small", "provider": "OpenAI", "dims": 1536, "price_per_m": 0.02, "env": "OPENAI_API_KEY", "litellm": "text-embedding-3-small", "note": "Strong general embeddings at 0.02 USD per million tokens."},
    "text-embedding-3-large": {"name": "OpenAI text-embedding-3-large", "provider": "OpenAI", "dims": 3072, "price_per_m": 0.13, "env": "OPENAI_API_KEY", "litellm": "text-embedding-3-large", "note": "Highest quality OpenAI embeddings at 0.13 USD per million tokens."},
    "gemini-embedding-001": {"name": "Gemini Embedding 001", "provider": "Google", "dims": 3072, "price_per_m": 0.15, "env": "GEMINI_API_KEY", "litellm": "gemini/gemini-embedding-001", "note": "Google's multilingual embeddings at 0.15 USD per million tokens."},
}

CHUNK_CHARS = 900
CHUNK_OVERLAP = 150
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
STOP = {"the", "and", "for", "that", "with", "this", "from", "are", "was", "were", "have", "has", "not", "but", "you", "your", "our", "can", "will", "all", "any", "per", "into", "than", "then", "them", "they", "their", "what", "when", "where", "which", "who", "how", "does", "did", "its", "it's"}

_matrix_cache: dict[str, tuple[int, np.ndarray, list[str]]] = {}
_cache_lock = threading.Lock()


# ------------------------------------------------------------------ text utilities ------------------------------------------------------------------

def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in STOP and len(t) > 1]


def chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Paragraph-aware chunks of about `size` characters with a small overlap, so citations stay readable."""
    text = re.sub(r"\r\n?", "\n", text).strip()
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paragraphs:
        while len(p) > size:  # very long paragraph: split on sentence boundaries
            cut = max(p.rfind(". ", 0, size), p.rfind("\n", 0, size), size // 2)
            piece, p = p[: cut + 1].strip(), p[cut + 1 :].strip()
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.append(piece)
        if len(buf) + len(p) + 2 <= size:
            buf = f"{buf}\n\n{p}" if buf else p
        else:
            if buf:
                chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)
    if overlap and len(chunks) > 1:
        out = [chunks[0]]
        for prev, cur in itertools.pairwise(chunks):
            tail = prev[-overlap:]
            out.append((tail[tail.find(" ") + 1 :] + " " + cur).strip() if " " in tail else cur)
        chunks = out
    return chunks


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


# ------------------------------------------------------------------ embeddings ------------------------------------------------------------------

def _hash_embed(texts: list[str], dims: int = 384) -> np.ndarray:
    out = np.zeros((len(texts), dims), dtype=np.float32)
    for i, text in enumerate(texts):
        toks = tokens(text)
        grams = toks + [f"{a}_{b}" for a, b in itertools.pairwise(toks)]
        for g in grams:
            h = int(hashlib.blake2b(g.encode(), digest_size=8).hexdigest(), 16)
            out[i, h % dims] += 1.0 if (h >> 63) else -1.0
        norm = np.linalg.norm(out[i])
        if norm:
            out[i] /= norm
    return out


def embedding_available(model_id: str) -> bool:
    spec = EMBEDDING_MODELS.get(model_id)
    if spec is None:
        return False
    if spec["env"] is None:
        return True
    import os

    return bool(os.environ.get(spec["env"])) or settings.fake_llm


def embedding_credentials(db: Session, user: User | None, model_id: str) -> dict:
    """The caller's own key for the embedding provider when they have one; empty means the platform key (environment)."""
    from app.keys import resolve_key

    spec = EMBEDDING_MODELS.get(model_id)
    if spec is None or spec["litellm"] is None or user is None:
        return {}
    secret, source, extra = resolve_key(db, user.id, spec["provider"], "knowledge")
    if source == "personal" and secret:
        return {"api_key": secret, **({"api_base": extra["api_base"]} if extra.get("api_base") else {})}
    return {}


def embed(model_id: str, texts: list[str], creds: dict | None = None) -> tuple[np.ndarray, int, float, int]:
    """Returns (vectors, tokens, cost_usd, latency_ms). Falls back to local vectors when a provider is unavailable or faked."""
    spec = EMBEDDING_MODELS.get(model_id) or EMBEDDING_MODELS["local-hash"]
    started = time.perf_counter()
    creds = creds or {}
    if spec["litellm"] is None or settings.fake_llm or (not creds and not embedding_available(model_id)):
        vecs = _hash_embed(texts, EMBEDDING_MODELS["local-hash"]["dims"])
        return vecs, sum(estimate_tokens(t) for t in texts), 0.0, int((time.perf_counter() - started) * 1000)
    import litellm

    vectors: list[list[float]] = []
    total_tokens = 0
    for start in range(0, len(texts), 64):
        batch = texts[start : start + 64]
        resp = litellm.embedding(model=spec["litellm"], input=batch, **creds)
        vectors.extend(item["embedding"] for item in resp.data)
        usage = getattr(resp, "usage", None)
        total_tokens += int(getattr(usage, "prompt_tokens", 0) or 0) or sum(estimate_tokens(t) for t in batch)
    arr = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    arr = arr / np.where(norms == 0, 1, norms)
    return arr, total_tokens, round(total_tokens / 1_000_000 * spec["price_per_m"], 8), int((time.perf_counter() - started) * 1000)


def _meter(db: Session, user_id: str, model_id: str, tokens_used: int, cost: float, latency_ms: int) -> None:
    spec = EMBEDDING_MODELS.get(model_id) or EMBEDDING_MODELS["local-hash"]
    db.add(UsageEvent(user_id=user_id, feature="knowledge", model=model_id, provider=spec["provider"], tokens_in=tokens_used, tokens_out=0, cost_usd=cost, latency_ms=latency_ms, status="ok"))


# ------------------------------------------------------------------ spaces ------------------------------------------------------------------

def visible_spaces(db: Session, user: User) -> list[KnowledgeSpace]:
    rows = db.scalars(select(KnowledgeSpace).order_by(KnowledgeSpace.updated_at.desc())).all()
    return [s for s in rows if can_see(s, user)]


def can_see(space: KnowledgeSpace, user: User) -> bool:
    return space.owner_id == user.id or user.role == "admin" or space.visibility == "org" or (space.visibility == "department" and space.department == user.department)


def can_edit(space: KnowledgeSpace, user: User) -> bool:
    return space.owner_id == user.id or user.role == "admin"


def space_payload(s: KnowledgeSpace, owner: User | None = None) -> dict:
    return {"id": s.id, "name": s.name, "description": s.description, "visibility": s.visibility, "department": s.department, "embedding_model": s.embedding_model, "embedding_name": EMBEDDING_MODELS.get(s.embedding_model, {}).get("name", s.embedding_model), "doc_count": s.doc_count, "chunk_count": s.chunk_count, "owner_id": s.owner_id, "owner_name": owner.name if owner else None, "created_at": s.created_at.isoformat(), "updated_at": s.updated_at.isoformat()}


def document_payload(d: KnowledgeDocument) -> dict:
    return {"id": d.id, "space_id": d.space_id, "title": d.title, "source_type": d.source_type, "source_ref": d.source_ref, "bytes": d.bytes, "chunk_count": d.chunk_count, "tokens": d.tokens, "cost_usd": d.cost_usd, "has_graph": bool(d.graph), "created_at": d.created_at.isoformat()}


def _invalidate(space_id: str) -> None:
    with _cache_lock:
        _matrix_cache.pop(space_id, None)


def _recount(db: Session, space: KnowledgeSpace) -> None:
    space.doc_count = int(db.scalar(select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.space_id == space.id)) or 0)
    space.chunk_count = int(db.scalar(select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.space_id == space.id)) or 0)


def ingest_text(db: Session, space: KnowledgeSpace, user: User, title: str, text: str, source_type: str = "text", source_ref: str = "", metas: list[dict] | None = None, chunks: list[str] | None = None, graph: dict | None = None) -> KnowledgeDocument:
    """Chunk, embed, store, meter. `chunks`/`metas` let structured sources (repositories, datasets) supply their own units."""
    pieces = chunks if chunks is not None else chunk_text(text)
    pieces = [p for p in pieces if p.strip()][:4000]
    doc = KnowledgeDocument(space_id=space.id, title=title[:255], source_type=source_type, source_ref=source_ref[:512], bytes=len(text.encode("utf-8")), graph=graph)
    db.add(doc)
    db.flush()
    if pieces:
        vecs, used, cost, latency = embed(space.embedding_model, pieces, embedding_credentials(db, user, space.embedding_model))
        db.bulk_save_objects([
            KnowledgeChunk(space_id=space.id, doc_id=doc.id, ordinal=i, text=piece, embedding=[round(float(x), 6) for x in vecs[i]], meta=(metas[i] if metas and i < len(metas) else {}))
            for i, piece in enumerate(pieces)
        ])
        doc.chunk_count, doc.tokens, doc.cost_usd = len(pieces), used, cost
        _meter(db, user.id, space.embedding_model, used, cost, latency)
    _recount(db, space)
    db.commit()
    _invalidate(space.id)
    return doc


def delete_document(db: Session, space: KnowledgeSpace, doc: KnowledgeDocument) -> None:
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.doc_id == doc.id))
    db.delete(doc)
    db.flush()
    _recount(db, space)
    db.commit()
    _invalidate(space.id)


def delete_space(db: Session, space: KnowledgeSpace) -> None:
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.space_id == space.id))
    db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.space_id == space.id))
    db.delete(space)
    db.commit()
    _invalidate(space.id)


# ------------------------------------------------------------------ retrieval ------------------------------------------------------------------

def _matrix(db: Session, space: KnowledgeSpace) -> tuple[np.ndarray, list[str]]:
    with _cache_lock:
        cached = _matrix_cache.get(space.id)
        if cached and cached[0] == space.chunk_count:
            return cached[1], cached[2]
    rows = db.execute(select(KnowledgeChunk.id, KnowledgeChunk.embedding).where(KnowledgeChunk.space_id == space.id).order_by(KnowledgeChunk.doc_id, KnowledgeChunk.ordinal)).all()
    ids = [r[0] for r in rows]
    mat = np.asarray([r[1] for r in rows], dtype=np.float32) if rows else np.zeros((0, 1), dtype=np.float32)
    with _cache_lock:
        _matrix_cache[space.id] = (space.chunk_count, mat, ids)
    return mat, ids


def _bm25(query_tokens: list[str], docs: list[list[str]], k1: float = 1.5, b: float = 0.75) -> list[float]:
    n = len(docs)
    if n == 0:
        return []
    avgdl = sum(len(d) for d in docs) / n or 1
    df: Counter[str] = Counter()
    for d in docs:
        df.update(set(d))
    scores = []
    for d in docs:
        tf = Counter(d)
        s = 0.0
        for q in query_tokens:
            if q not in tf:
                continue
            idf = math.log(1 + (n - df[q] + 0.5) / (df[q] + 0.5))
            s += idf * tf[q] * (k1 + 1) / (tf[q] + k1 * (1 - b + b * len(d) / avgdl))
        scores.append(s)
    return scores


def search(db: Session, space: KnowledgeSpace, query: str, k: int = 5) -> list[dict]:
    """Hybrid retrieval: cosine over embeddings and BM25 over tokens, fused with reciprocal rank fusion."""
    mat, ids = _matrix(db, space)
    if not ids:
        return []
    qvec, _, _, _ = embed(space.embedding_model, [query])
    dense = (mat @ qvec[0]).tolist() if mat.shape[1] == qvec.shape[1] else [0.0] * len(ids)
    chunk_rows = {c.id: c for c in db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.id.in_(ids))).all()}
    ordered = [chunk_rows[i] for i in ids if i in chunk_rows]
    sparse = _bm25(tokens(query), [tokens(c.text) for c in ordered])
    dense_rank = {i: r for r, i in enumerate(sorted(range(len(ordered)), key=lambda i: -dense[i]))}
    sparse_rank = {i: r for r, i in enumerate(sorted(range(len(ordered)), key=lambda i: -sparse[i]))}
    fused = []
    for i, c in enumerate(ordered):
        if dense[i] <= 0 and sparse[i] <= 0:
            continue
        fused.append((1 / (60 + dense_rank[i]) + 1 / (60 + sparse_rank[i]), i, c))
    fused.sort(key=lambda t: -t[0])
    docs = {d.id: d for d in db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.space_id == space.id)).all()}
    out = []
    for score, i, c in fused[:k]:
        d = docs.get(c.doc_id)
        out.append({"chunk_id": c.id, "doc_id": c.doc_id, "title": d.title if d else "", "source_type": d.source_type if d else "", "ordinal": c.ordinal, "text": c.text, "meta": c.meta or {}, "score": round(score * 100, 3), "dense": round(float(dense[i]), 4), "sparse": round(float(sparse[i]), 3), "cite": f"{(d.title if d else 'doc')[:60]}#{c.ordinal + 1}"})
    return out


# ------------------------------------------------------------------ ingestion sources ------------------------------------------------------------------

def extract_text(filename: str, content: bytes) -> str:
    """Plain text from the formats people actually upload: text, markdown, csv, json, html, pdf, docx."""
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages[:400])
    if name.endswith(".docx"):
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", "ignore")
        xml = re.sub(r"</w:p>", "\n\n", xml)
        return html.unescape(re.sub(r"<[^>]+>", "", xml))
    text = content.decode("utf-8", "ignore")
    if name.endswith((".html", ".htm")):
        return html_to_text(text)
    return text


def html_to_text(markup: str) -> str:
    markup = re.sub(r"(?is)<(script|style|nav|footer|noscript)[^>]*>.*?</\1>", " ", markup)
    markup = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|br|section|article)>", "\n\n", markup)
    text = html.unescape(re.sub(r"<[^>]+>", " ", markup))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", text)).strip()


def fetch_url(url: str) -> tuple[str, str]:
    """Returns (title, text). Only http(s), with a size cap."""
    if not re.match(r"^https?://", url):
        raise ValueError("Only http and https URLs can be imported")
    with httpx.Client(timeout=20, follow_redirects=True, headers={"user-agent": "enterprise-ai-playground/0.7"}) as client:
        r = client.get(url)
        r.raise_for_status()
        body = r.content[:3_000_000]
    ctype = r.headers.get("content-type", "")
    if "pdf" in ctype or url.lower().endswith(".pdf"):
        return url.rsplit("/", 1)[-1], extract_text("page.pdf", body)
    markup = body.decode("utf-8", "ignore")
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", markup)
    title = html.unescape(m.group(1)).strip() if m else url
    return title[:200], html_to_text(markup) if "html" in ctype or "<html" in markup[:2000].lower() else markup


def decode_upload(content_base64: str) -> bytes:
    return base64.b64decode(content_base64)


def dataset_units(dataset: str) -> tuple[str, list[str], list[dict]]:
    """Mock datasets become one chunk per record so answers can cite the record id."""
    from app.agents.data import DATASETS, load_csv, load_json

    spec = next((d for d in DATASETS if d["id"] == dataset), None)
    if spec is None:
        raise ValueError(f"Unknown dataset {dataset}")
    rows = load_csv(spec["file"]) if spec["file"].endswith(".csv") else load_json(spec["file"])
    if isinstance(rows, dict):
        rows = [{"id": k, "items": v} for k, v in rows.items()]
    chunks, metas = [], []
    for row in rows[:2000]:
        rid = str(row.get("id") or row.get("invoice_id") or row.get("po_id") or row.get("contract_id") or len(chunks) + 1)
        body = "\n".join(f"{k}: {v}" for k, v in row.items() if not isinstance(v, list | dict)) or str(row)
        chunks.append(f"{spec['title']} record {rid}\n{body}")
        metas.append({"record_id": rid, "dataset": dataset})
    return spec["title"], chunks, metas
