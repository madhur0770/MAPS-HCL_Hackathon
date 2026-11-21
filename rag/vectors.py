"""Vector index (semantic search). Each document section gets an embedding from Ollama; vectors are stored in the SQLite
table `embeddings` (keyed by a hash of the text, so unchanged text is never embedded twice) and compared by cosine similarity.
Results are fused with BM25 and character n-grams by reciprocal rank fusion in rag/retrieval.py.
Without Ollama (or with USE_VECTORS=false) nothing here runs and retrieval stays lexical."""
import hashlib
import json
import math

from assistant import llm
from core import config

_embedder = None          # tests plug in a fake embedder here


def set_embedder(fn):
    global _embedder
    _embedder = fn


def _embed(texts):
    if _embedder:
        return _embedder(texts)
    return llm.embed(texts)


def enabled():
    return config.USE_VECTORS() and (_embedder is not None or llm.available())


def _key(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _norm(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def attach(db, index):
    """Give every item of the lexical index a vector. Returns True when the index can do semantic search."""
    index.vec_ready = False
    if not enabled() or not index.items:
        return False
    model = "fake" if _embedder else config.OLLAMA_EMBED_MODEL()
    keys = [_key(it["text"][:2000]) for it in index.items]
    have = {}
    for i in range(0, len(keys), 500):
        part = keys[i:i + 500]
        q = "SELECT key, vec FROM embeddings WHERE model=? AND key IN (%s)" % ",".join("?" * len(part))
        for k, v in db.execute(q, [model] + part):
            have[k] = json.loads(v)
    missing = [i for i, k in enumerate(keys) if k not in have]
    for b in range(0, len(missing), 16):
        chunk = missing[b:b + 16]
        vecs = _embed([index.items[i]["text"][:2000] for i in chunk])
        if not vecs:
            return False                       # Ollama went away: stay lexical, try again later
        for i, v in zip(chunk, vecs):
            v = _norm(v)
            have[keys[i]] = v
            db.execute("INSERT OR REPLACE INTO embeddings(key, model, dim, vec) VALUES (?,?,?,?)", (keys[i], model, len(v), json.dumps(v)))
    db.commit()
    for it, k in zip(index.items, keys):
        it["vec"] = have[k]
    index.vec_ready = True
    return True


def scores(index, query):
    """Cosine similarity of the query to every item, as [(score, item_index)]. Empty when vectors are not ready."""
    if not getattr(index, "vec_ready", False):
        return []
    qv = _embed([query])
    if not qv:
        return []
    q = _norm(qv[0])
    return [(sum(a * b for a, b in zip(q, it["vec"])), i) for i, it in enumerate(index.items)]
