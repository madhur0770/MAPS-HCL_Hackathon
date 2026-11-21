"""Multi-turn behaviour: the assistant must carry context from earlier messages (route, date, class, booking, last rules question)."""
import pytest
from fastapi.testclient import TestClient
from core import db as dbm, seed
from app.main import make_app


@pytest.fixture()
def c(monkeypatch):
    monkeypatch.setenv("DEMO_NOW", "2026-11-21T10:00:00+05:30")
    d = dbm.connect(":memory:")
    seed.seed(d)
    return TestClient(make_app(d))


def say(c, sid, msg):
    r = c.post("/chat", json={"session_id": sid, "message": msg}, headers={"X-Passenger-Id": "P001"})
    assert r.status_code == 200
    return r.json()


def test_search_followups(c):
    say(c, "a", "trains from arunoday to chetakgarh tomorrow")
    a = say(c, "a", "what about the day after")
    assert "23 Nov" in a["answer"] and "Arunoday" in a["answer"]
    a = say(c, "a", "cheapest one?")
    assert a["answer_type"] == "answer" and "Cheapest" in a["answer"]
    a = say(c, "a", "which is the fastest")
    assert "Fastest" in a["answer"]
    a = say(c, "a", "kitna kharcha")
    assert "₹" in a["answer"]


def test_book_from_search_context(c):
    say(c, "b", "arunoday to chetakgarh 27 nov")
    a = say(c, "b", "book the first one")
    assert "class" in a["answer"].lower()
    a = say(c, "b", "AC3")
    assert "traveller" in a["answer"].lower()
    a = say(c, "b", "Rahul 30 and Meera 28")
    assert a["answer_type"] == "confirm_needed" and "UJ1006" in a["answer"]


def test_refund_after_cancel_preview_and_rules_followup(c):
    say(c, "r", "BKG0001 status")
    a = say(c, "r", "what is the refund")
    assert "₹2,802" in a["answer"]
    a = say(c, "t", "tatkal charges?")
    assert "AC2" in a["answer"] and "AC3" in a["answer"]
    a = say(c, "t", "and for AC3?")
    assert "₹330" in a["answer"] and "AC2" not in a["answer"]


def test_smalltalk_and_problem_reports(c):
    assert "welcome" in say(c, "s", "thanks")["answer"].lower()
    assert "Goodbye" in say(c, "s", "bye")["answer"]
    assert "train search" in say(c, "s", "what can you do")["answer"]
    a = say(c, "s", "i lost my wallet on train")
    assert "station called" not in a["answer"] and "Please tell me where" not in a["answer"]
    a = say(c, "s", "my train is late what do i do")
    assert "station called" not in a["answer"]


def test_single_station_without_role_asks_instead_of_guessing(c):
    a = say(c, "q", "I need a ticket anpn")
    assert "start" in a["answer"].lower() and "Anandpur North" in a["answer"]
    a = say(c, "q", "to")
    assert "travelling from" in a["answer"] or "from" in a["answer"]
    a = say(c, "q", "Arunoday and date 30-11-2026")
    assert "Arunoday to Anandpur North" in a["answer"], a["answer"]
    a = say(c, "q2", "I need a ticket anpn")
    a = say(c, "q2", "arunoday 30 nov 2026")          # a bare second station: the first one is the start
    assert "Anandpur North to Arunoday" in a["answer"], a["answer"]
