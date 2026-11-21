"""Vector search and Ollama-assisted understanding, tested with fakes (Ollama is not needed to run these)."""
import pytest
from fastapi.testclient import TestClient
from core import db as dbm, seed
from app.main import make_app
from assistant import llm
from rag import vectors, store, retrieval

H = {"X-Passenger-Id": "P001"}


@pytest.fixture()
def app_db(monkeypatch):
    monkeypatch.setenv("DEMO_NOW", "2026-11-21T10:00:00+05:30")
    d = dbm.connect(":memory:")
    seed.seed(d)
    return d


def chat(c, msg, sid="v1"):
    r = c.post("/chat", json={"session_id": sid, "message": msg}, headers=H)
    assert r.status_code == 200, r.text
    return r.json()


def test_missing_preposition_unknown_city(app_db):
    c = TestClient(make_app(app_db))
    for msg in ("i need a ticket delhi", "need ticket delhi", "book ticket delhi tomorrow"):
        a = chat(c, msg, sid=msg)
        assert a["answer_type"] == "clarification", (msg, a["answer"])
        assert "Delhi" in a["answer"] and "not sure I understood" not in a["answer"], a["answer"]


def test_missing_preposition_typo_is_repaired(app_db):
    c = TestClient(make_app(app_db))
    a = chat(c, "need a ticket suryanagr")
    assert "where you are going" in a["answer"] and "not sure I understood" not in a["answer"]   # typo repaired to a real station, asks for the rest


def test_vector_fusion_finds_paraphrase(app_db):
    """A fake embedder that maps related words to the same dimension: a question with no shared keyword still finds the section."""
    groups = [("refund", "money", "reimburse", "cancel", "cancellation"), ("tatkal", "urgent", "emergency", "lastminute"),
              ("pet", "dog", "animal", "cat"), ("luggage", "baggage", "bag")]

    def fake(texts):
        out = []
        for t in texts:
            low = t.lower()
            out.append([float(sum(low.count(w) for w in g)) + 0.001 for g in groups])
        return out

    vectors.set_embedder(fake)
    try:
        store.invalidate(app_db)
        idx = store.get_index(app_db)
        assert idx.vec_ready is True
        n = app_db.execute("SELECT count(*) FROM embeddings").fetchone()[0]
        assert n > 0
        res, _ = idx.search("will I get my money back", k=5)
        assert res and idx.last_vec_top > 0.9            # the vector list took part in the fusion
        best = max(vectors.scores(idx, "will I get my money back"))
        assert any(w in idx.items[best[1]]["text"].lower() for w in ("refund", "money", "cancel"))   # 'money' shares no word with 'refund' lexically
        # a second build reads vectors from SQLite and does not embed again
        calls = []
        vectors.set_embedder(lambda t: calls.append(t) or fake(t))
        store.invalidate(app_db)
        store.get_index(app_db)
        assert calls == []
    finally:
        vectors.set_embedder(None)
        store.invalidate(app_db)


def test_vectors_fall_back_when_embedder_fails(app_db):
    vectors.set_embedder(lambda texts: None)
    try:
        store.invalidate(app_db)
        idx = store.get_index(app_db)
        assert idx.vec_ready is False
        res, top = idx.search("how much is the refund for cancelling", k=3)
        assert res and top > 0
    finally:
        vectors.set_embedder(None)
        store.invalidate(app_db)


def test_llm_places_used_only_when_valid(app_db, monkeypatch):
    c = TestClient(make_app(app_db))
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "suggest_intent", lambda *a, **k: None)
    # model names a real city from the list -> the search runs
    monkeypatch.setattr(llm, "extract_places", lambda text, cities: {"from": "Suryanagar", "to": "Anandpur"})
    a = chat(c, "i need a ticket delhii", sid="l1")
    assert a["answer_type"] != "not_found"
    # model invents something -> ignored, the passenger still gets the unknown-place prompt
    monkeypatch.setattr(llm, "extract_places", lambda text, cities: {"to": "Atlantis"})
    a = chat(c, "i need a ticket delhii", sid="l2")
    assert a["answer_type"] == "clarification" and "Delhii" in a["answer"]


def test_ollama_probe_is_off_with_mock(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "true")
    assert llm.available() is False
    assert llm.embed(["x"]) is None


def test_followups_keep_context(app_db):
    c = TestClient(make_app(app_db))
    chat(c, "trains from Arunoday to Anandpur North on 30 Nov 2026", sid="f1")
    a = chat(c, "is there a AC3 seat on UJ1024", sid="f1")
    assert "UJ1024" in a["answer"] and "AC3" in a["answer"] and "Arunoday" in a["answer"], a["answer"]
    assert "UJ1020" not in a["answer"]
    a = chat(c, "what about 1 Dec 2026", sid="f1")
    assert "Arunoday" in a["answer"] and "1 Dec" in a["answer"], a["answer"]
    a = chat(c, "AC2 only", sid="f1")
    assert "AC2" in a["answer"] and "Arunoday" in a["answer"], a["answer"]


def test_full_anandpur_flow_from_screenshot(app_db):
    c = TestClient(make_app(app_db))
    a = chat(c, "i need a ticket to delhi", sid="g1")
    assert "Delhi" in a["answer"]
    a = chat(c, "I need a ticket to anandpur", sid="g2")
    assert "Anandpur North" in a["answer"]
    a = chat(c, "ANPN", sid="g2")
    assert "from" in a["answer"]
    a = chat(c, "Arunoday and date 30-11-2026", sid="g2")
    assert "UJ1024" in a["answer"]
    a = chat(c, "is there a AC3 seat on UJ1024", sid="g2")
    assert "UJ1024" in a["answer"] and "AC3" in a["answer"] and "Please tell me" not in a["answer"], a["answer"]
