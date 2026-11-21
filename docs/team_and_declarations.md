# Who built what

**Team: MAPS (HCLTech AI Engineer on-campus hackathon, 21 Nov 2026).** Fill the names in; the file mapping follows the repository layout. Each member must be able to explain every file listed in their row and answer questions on the rest.

| Member | Name | Roll / ID | Built (files) | Technique to explain |
|---|---|---|---|---|
| 1 | ______________ | ________ | Data and rules: `data_kit/`, `core/` (`db.py`, `seed.py`, `official.py`), `docs/documents_list.md`, `docs/data_card.md` | schema, generator and checker, document precedence data |
| 2 | ______________ | ________ | Tools and actions: `tools/` (refund, fares, seats, timetable, deadlines), `actions/manager.py` | integer-paise refund bands, propose/confirm/execute/verify, idempotency |
| 3 | ______________ | ________ | Assistant brain and search: `assistant/`, `rag/` | pipeline, intents in en/hi/hinglish, BM25 + n-grams + rank fusion, abstain, precedence, injection sanitising |
| 4 | ______________ | ________ | API, UI, deployment, evaluation: `app/`, `ui-react/`, `ui/`, `Dockerfile`, `docker-compose.yml`, `eval/`, `scripts/`, `tests/` | endpoints, identity header, evaluation oracles, red-team and robustness suites |

Roles can be re-assigned: edit the table so it states what each person really did. AI assistance is described in `ai_use.md`.

# Declarations

Original-work declarations are in `docs/declarations/`: one form per member (`declaration_member_1.md` ... `_4.md`). **Nothing is signed by the assistant.** Each member fills in their own name and ID, signs (print and scan, or sign the organisers' official form and add the scan to this folder), and the team commits the signed copies before the `final` tag is moved to the last commit.
