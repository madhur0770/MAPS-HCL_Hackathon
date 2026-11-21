"""Keeps one search index in memory; rebuilt whenever documents change (live ingest, no restart)."""
import threading
import time
from rag.retrieval import Index

_lock = threading.Lock()
_cache = {}


def docs_from_db(db):
    """Documents as the search sees them. Any sentence that tries to give the assistant an order ("ignore all previous instructions...") is dropped
    here, so a poisoned FAQ or circular can never reach an answer; the stored original is untouched."""
    from rag.ingest import sanitize
    out = []
    for r in db.execute("SELECT * FROM documents"):
        d = dict(r)
        d["text"], _ = sanitize(d["text"])
        out.append(d)
    return out


def get_index(db):
    key = id(db)
    ver = db.execute("SELECT count(*), coalesce(max(added_at),'') FROM documents").fetchone()
    sig = (ver[0], ver[1])
    with _lock:
        c = _cache.get(key)
        if c and c[0] == sig:
            idx = c[1]
            if not getattr(idx, "vec_ready", False) and time.time() - c[2] > 60:       # Ollama may have started since: try the vectors again
                try:
                    from rag import vectors
                    vectors.attach(db, idx)
                except Exception:
                    pass
                _cache[key] = (sig, idx, time.time())
            return idx
        idx = Index(docs_from_db(db))
        try:
            from rag import vectors
            vectors.attach(db, idx)            # semantic vectors when Ollama (or a test embedder) is available
        except Exception:
            idx.vec_ready = False
        _cache[key] = (sig, idx, time.time())
        return idx


def invalidate(db):
    with _lock:
        _cache.pop(id(db), None)
