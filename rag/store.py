"""Keeps one search index in memory; rebuilt whenever documents change (live ingest, no restart)."""
import threading
from rag.retrieval import Index

_lock = threading.Lock()
_cache = {}


def docs_from_db(db):
    return [dict(r) for r in db.execute("SELECT * FROM documents")]


def get_index(db):
    key = id(db)
    ver = db.execute("SELECT count(*), coalesce(max(added_at),'') FROM documents").fetchone()
    sig = (ver[0], ver[1])
    with _lock:
        c = _cache.get(key)
        if c and c[0] == sig:
            return c[1]
        idx = Index(docs_from_db(db))
        _cache[key] = (sig, idx)
        return idx


def invalidate(db):
    with _lock:
        _cache.pop(id(db), None)
