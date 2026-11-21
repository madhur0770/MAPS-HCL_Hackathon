"""Search the documents. Plain Python, no external search library (so we can explain every line).
 1. split every document into sections
 2. rank sections with BM25 (word match) and char-n-gram TF-IDF (handles spelling variations), fuse with RRF
 3. keep only documents that are IN FORCE at as_of
 4. precedence: circular beats the rule it replaces; rules beat FAQs; newer beats older; flag clashes
 5. abstain (not_found) when nothing relevant is found
"""
import math

from core import config
import re
from collections import Counter

from rag import synonyms

SEC_RE = re.compile(r"(?m)^(Section\s+\d+(?:\.\d+)?)\s*:\s*")


STOP = set("""a an the is are was were be i me my we our you your it its this that of to for on in at by and or if
can could will would should do does did how much many what when where which who whom why please tell about from with
get got have has had not no yes there their them then than so as any some one also kya hai hain kitna kitni kitne mera meri
mere ko se me mein ka ki ke ho hoga hogi karna kar karne kaise kab kahan aap hum main par aur ya to toh ye yeh wo
कितना कितनी कितने करने पर का की के है हैं को से में और या क्या कैसे कब मेरा मेरी मेरे""".split())


def stem(w: str) -> str:
    if w in ("children", "kids"):
        return "child"
    if w.isascii() and len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def tokenize(text: str):
    return [stem(w) for w in re.findall(r"[\wऀ-ॿ]+", text.lower())]


def split_sections(doc):
    text = doc["text"]
    parts = SEC_RE.split(text)
    out = []
    if len(parts) <= 1:
        out.append(("Section 1", text.strip()))
    else:
        for i in range(1, len(parts), 2):
            out.append((parts[i].strip(), parts[i + 1].strip()))
    return out


def ngrams(text, lo=3, hi=5):
    out = Counter()
    for w in tokenize(text):
        w = " %s " % w
        for n in range(lo, hi + 1):
            for i in range(len(w) - n + 1):
                out[w[i:i + n]] += 1
    return out


class Index:
    def __init__(self, docs):
        self.items = []
        for d in docs:
            for sec, body in split_sections(d):
                full = "%s %s %s" % (d["title"], d["topic"], body)
                self.items.append({"doc": d, "section": sec, "text": body, "tokens": tokenize(full),
                                   "grams": ngrams(full)})
        n = len(self.items)
        self.N = n
        self.avgdl = sum(len(i["tokens"]) for i in self.items) / max(1, n)
        df = Counter()
        gdf = Counter()
        for it in self.items:
            df.update(set(it["tokens"]))
            gdf.update(set(it["grams"]))
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.gidf = {t: math.log(1 + n / c) for t, c in gdf.items()}
        for it in self.items:
            it["tf"] = Counter(it["tokens"])
            v = {g: (1 + math.log(c)) * self.gidf[g] for g, c in it["grams"].items()}
            it["gvec"] = v
            it["gnorm"] = math.sqrt(sum(x * x for x in v.values())) or 1.0

    def bm25(self, qtokens, it, k1=1.4, b=0.75):
        s, dl = 0.0, len(it["tokens"])
        for t in set(qtokens):
            f = it["tf"].get(t, 0)
            if f:
                s += self.idf.get(t, 0) * f * (k1 + 1) / (f + k1 * (1 - b + b * dl / self.avgdl))
        return s

    def cos(self, qgrams, it):
        qv = {g: (1 + math.log(c)) * self.gidf.get(g, 0) for g, c in qgrams.items()}
        qn = math.sqrt(sum(x * x for x in qv.values())) or 1.0
        dot = sum(w * it["gvec"].get(g, 0) for g, w in qv.items())
        return dot / (qn * it["gnorm"])

    def search(self, query: str, k=8):
        q = [t for t in synonyms.expand(tokenize(query)) if t not in STOP]
        if not any(not t.isdigit() for t in q):
            return [], 0.0
        if any(not t.isdigit() for t in q):
            q = [t for t in q if not t.isdigit() or len(q) > 6]       # a number alone ("2+2") must not find a rule
        qtext = " ".join(q)
        qg = ngrams(qtext)
        b = [(self.bm25(q, it), i) for i, it in enumerate(self.items)]
        c = [(self.cos(qg, it), i) for i, it in enumerate(self.items)]
        rank = {}
        v = []
        try:
            from rag import vectors
            v = vectors.scores(self, query)            # [] when Ollama / embeddings are not available
        except Exception:
            v = []
        self.last_vec_top = max([x for x, _ in v] + [0.0])
        for lst in ([b, c, v] if v else [b, c]):
            for r, (s, i) in enumerate(sorted(lst, reverse=True)[:30]):
                if s > 0:
                    rank[i] = rank.get(i, 0) + 1.0 / (60 + r + 1)
        top_bm = max([s for s, _ in b] + [0.0])
        if v and self.last_vec_top >= config.VECTOR_MIN() and top_bm < 2.5:
            top_bm = 2.5                  # a paraphrase with few shared words: the vector match is strong enough to answer
        res = []
        for i, sc in sorted(rank.items(), key=lambda kv: -kv[1])[:k]:
            it = self.items[i]
            res.append({"doc_id": it["doc"]["doc_id"], "section": it["section"], "text": it["text"], "score": sc,
                        "bm25": b[i][0], "cos": c[i][0], "doc": it["doc"]})
        return res, top_bm


def numbers_in(text):
    """Numbers that carry a fact. Document ids (RUL-005), section references (Section 3.2, Sections 3.1 to 3.4) and dates are ignored."""
    text = re.sub(r"\b[A-Z]{2,4}-[A-Z0-9-]*\d+\b", " ", text)
    text = re.sub(r"(?i)\bsections?\s+\d+(?:\.\d+)?(?:\s*(?:to|and|,|-)\s*\d+(?:\.\d+)?)*", " ", text)
    text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", text)
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def applicable(doc, as_of_date: str) -> bool:
    return doc["effective_from"] <= as_of_date


def retrieve(index: Index, query: str, as_of_date: str, topic=None, min_bm25=2.5):
    """Returns {'winner', 'hits', 'overridden', 'upcoming', 'abstain'}"""
    hits, top_bm = index.search(query, k=10)
    # drop documents not yet in force; remember future ones so we can mention them
    upcoming = [h for h in hits if not applicable(h["doc"], as_of_date)]
    hits = [h for h in hits if applicable(h["doc"], as_of_date)]
    if topic:
        t = [h for h in hits if h["doc"]["topic"] == topic]
        hits = t or hits
    if not hits or top_bm < min_bm25:
        return {"winner": None, "hits": hits, "overridden": [], "upcoming": upcoming, "abstain": True}
    # precedence among hits that share the winner's topic
    best_topic = hits[0]["doc"]["topic"]
    same = [h for h in hits if h["doc"]["topic"] == best_topic]
    in_force_ids = {h["doc"]["doc_id"] for h in same}
    # a rule SECTION is superseded when an applicable circular on the same topic amends that section
    # (the circular says "Original rule: RUL-005 / Original section: 3.3"); a circular that names no section replaces the whole rule
    amended, whole = set(), set()
    for d in (i["doc"] for i in index.items):
        pass
    seen = set()
    for it in index.items:
        d = it["doc"]
        if d["doc_id"] in seen or d["doc_type"] != "circular" or not d["supersedes"] or d["topic"] != best_topic or not applicable(d, as_of_date):
            continue
        seen.add(d["doc_id"])
        full = " ".join(x["text"] for x in index.items if x["doc"]["doc_id"] == d["doc_id"])
        secs = re.findall(r"Original section:\s*([\d.]+)", full)
        rel = re.findall(r"Related repeated provision:\s*([A-Z]+-\d+)\s*Sections?\s*([\d.]+)", full)
        if secs:
            amended.update((d["supersedes"], x) for x in secs)
            amended.update(rel)
        else:
            whole.add(d["supersedes"])
    all_applicable_sup = whole

    def key(h):
        d = h["doc"]
        sec = h["section"].replace("Section ", "")
        superseded = d["doc_id"] in all_applicable_sup or (d["doc_id"], sec) in amended
        # lower tuple sorts first: not-superseded, lower authority number, newer date, higher score
        return (1 if superseded else 0, d["authority"], _neg_date(d["effective_from"]), -h["score"])

    # authority (rule > circular > FAQ) decides only between sections that are about equally relevant to the question
    top = max(same, key=lambda h: (h["bm25"], h["score"]))
    close = [h for h in same if h is top or h["bm25"] >= 0.55 * top["bm25"]]
    rest = [h for h in same if h not in close]
    ranked = sorted(close, key=key) + sorted(rest, key=lambda h: -h["score"])
    # a circular that replaces a rule is shown first, but the rule's sections keep their own value
    winner = ranked[0]
    if winner["doc"]["doc_type"] == "circular":
        # a circular only wins for the section it amends: if the question matches a DIFFERENT section of the rule better, answer from that section
        m_doc = re.search(r"Original rule:\s*([A-Z]+-\d+)", winner["text"])
        m_sec = re.search(r"Original section:\s*([\d.]+)", winner["text"])
        amended = ((m_doc.group(1) if m_doc else None), (m_sec.group(1) if m_sec else None))
        for h in ranked[1:]:
            if h["doc"]["doc_type"] == "circular":
                continue
            hs = h["section"].replace("Section ", "")
            if h["bm25"] > winner["bm25"] * 1.1 and not (h["doc_id"] == amended[0] and hs == amended[1]) and h["doc"]["topic"] == winner["doc"]["topic"]:
                ranked.remove(h)
                ranked.insert(0, h)
                winner = h
                break
    over = []
    wn = numbers_in(winner["text"])
    for h in ranked[1:]:
        if h["doc"]["doc_id"] == winner["doc"]["doc_id"]:
            continue
        hn = numbers_in(h["text"])
        if hn and wn and (hn - wn) and (wn - hn) and (h["doc"]["authority"] > winner["doc"]["authority"] or h["doc"]["doc_id"] in all_applicable_sup):
            over.append({"doc_id": h["doc"]["doc_id"], "section": h["section"], "why": "older or lower authority and its figures differ"})
    return {"winner": winner, "hits": ranked, "overridden": over, "upcoming": upcoming, "abstain": False}


def _neg_date(d):
    # newer date first: turn yyyy-mm-dd into negative integer
    return -int(d.replace("-", ""))
