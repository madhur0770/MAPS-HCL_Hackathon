# Who built what

**Team MAPS: HCLTech AI Engineer on-campus hackathon, 21 Nov 2026.** Project: Train Travel Assistant for Ujjwal Rail. Each member can explain every file in their row and answers questions on the rest. AI assistance is described in `ai_use.md`.

| Member | Main responsibility | Also owns (remaining functions, divided by theme) | Files |
|---|---|---|---|
| **Akash Soni** | Evaluation, input cases and testing | Data kit checks and input data (prompts, generator and validators), audit samples, test reports | `eval/` (40-question CSV, 66-question set, 98-case robustness suite, reports), `tests/` (unit, API, red-team), `scripts/check_all.py`, `run_eval.py`, `run_csv_eval.py`, `run_robust.py`, `stress.py`, `validate_data.py`, `make_audit_samples.py`, `data_kit/` (generation prompts, `generate_railway_data.py`, `validate_*.py`, kit tests), `docs/audit_samples/`, `docs/data_card.md`, `docs/documents_list.md` |
| **Praveen** | Delivery and UI | Docker and deployment, CI, setup and run scripts, README run instructions, submission pack | `ui-react/` (React chat app, built into `app/static/`), `ui/streamlit_app.py`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `.github/workflows/ci.yml`, `scripts/setup.ps1`, `run_local.ps1`, `update.ps1`, `docs/SUBMISSION.md`, `README.md` |
| **Sufiyan** | Orchestrator, backend logic, RAG, tools | Understanding in English/Hindi/Hinglish (intents, dates, spelling repair, reply templates), API endpoints, database and data loading, document search and precedence | `assistant/router.py` (the 9-step pipeline), `understand.py`, `dates.py`, `typos.py`, `i18n.py`, `language.py`; `tools/` (timetable, fares, seats, bookings, deadlines, refund calculator); `rag/retrieval.py`, `rag/store.py`, `rag/synonyms.py`; `app/main.py`, `app/schemas.py`; `core/` (`db.py`, `seed.py`, `official.py`, `config.py`, `clock.py`), `docs/architecture.md` |
| **Madhur** | LLM, tools, actions, human in the loop, RAG | Safety and privacy guards, number and citation checks, document ingestion and vector search | `assistant/llm.py` (optional Ollama: intent suggestion, wording, embeddings), `assistant/handoff.py` (human desks, targets, summaries), `assistant/guardrails.py`, `assistant/correctors.py`; `actions/manager.py` (propose, Confirm, execute, verify, idempotency); `tools/refund.py` (refund bands, with Sufiyan); `rag/ingest.py` (live document ingest, sanitising), `rag/vectors.py` (embeddings, rank fusion with BM25); `docs/ai_use.md` |

Shared work: the pipeline was designed together; `tools/` is Sufiyan's (search, seats, fares) and Madhur's (refund, actions); RAG is Sufiyan's (retrieval, precedence) and Madhur's (ingest, vectors).

# Declarations

Original-work declarations are in `docs/declarations/`: one form per member, with the name filled in. **Nothing is signed by the assistant.** Each member adds their roll number, signs (print and scan, or attach the organisers' official form as `declaration_member_N_signed.pdf`), and the team commits the signed copies before the `final` tag is created.
