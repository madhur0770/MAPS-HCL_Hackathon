# AI use note

**Short version:** Claude (Anthropic's Claude Code assistant, Sonnet 5.5) drafted nearly all of the code, tests, evaluation harnesses and documents in this repository, working in a session directed by the team. The team supplied the brief and the data kit, decided what to build, ran and stress-tested the application, reported failures (often as screenshots), and asked for the fixes. Every member must be able to explain every file; AI assistance does not change who is responsible for the work.

## 1. Where AI tools were used to BUILD this (by area)

| Area | Files | AI assistance | Team contribution |
|---|---|---|---|
| Pipeline, understanding, templates | `assistant/router.py`, `understand.py`, `dates.py`, `typos.py`, `i18n.py`, `language.py` | Claude wrote and repeatedly fixed these | Chose the design (rules first, model optional); found failures by hand-testing in English, Hindi and Hinglish and sent screenshots; the fixes followed |
| Tools and actions | `tools/*`, `actions/manager.py` | Claude wrote them from the rule text | Reviewed the refund bands and cut-offs against the policy documents; asked for edge cases (48h, 12h, 4h, operator cancellation, tatkal) |
| Search and documents | `rag/*` | Claude wrote retrieval, precedence, ingest, sanitising, optional vectors | Chose hybrid lexical-first search; tested live ingest of circulars and poisoned documents |
| Safety and handoff | `assistant/guardrails.py`, `handoff.py`, `correctors.py` | Claude wrote them | Supplied attack prompts and admin / injection / false-policy screenshots; decided hand-over desks and targets from RUL-012 |
| API and database | `app/`, `core/` | Claude wrote them | Reviewed endpoints against the brief |
| UI | `ui-react/`, `ui/streamlit_app.py` | Claude wrote the React and Streamlit apps | Tested in the browser; asked for the bookings list, sorting, traveller selection and other changes |
| Delivery | `Dockerfile`, `docker-compose.yml`, `.github/`, `scripts/*.ps1` | Claude wrote them | Ran the setup and run scripts on Windows and reported errors. **Docker was not run in the AI session; the team must test it** |
| Tests | `tests/` (188 tests) | Claude wrote them | Added cases from their own failures |
| Evaluation | `eval/csv_eval.py`, `questions.jsonl`, `cases.py`, `robust_eval.py`, `scripts/run_*eval.py`, `run_robust.py` | Claude wrote the harnesses, oracles, fuzzer and reports | The 40-question CSV and the 98-case robustness workbook were **supplied to us**; we asked for them to be run, including Hindi/Hinglish variations, and for the bugs they found to be fixed |
| Data kit tooling | `data_kit/` | The prompts, generator and validators in the kit are part of the supplied kit; Claude's changes are limited to the loader (`core/official.py`) and checks that use it | Supplied the kit |
| Documents | `README.md`, `docs/*`, audit samples | Claude drafted the text; the audit samples are produced by running `scripts/make_audit_samples.py` | Team edits and fills in names, signatures and declarations |

The git history shows the AI's work: commit messages carry `Co-Authored-By: Claude` and a session link.

## 2. Where AI is used at RUN time

Only an **optional** local model (Ollama). With `MOCK_LLM=true` (the default) no model runs, and every evaluation result in this repository was produced that way.
1. It may suggest an intent, or read a place name, when the rules are unsure. The suggestion is accepted only if it resolves to a real station or a listed intent.
2. It may reword an answer that was made from documents. The number check and citation check still apply.
3. It makes embeddings (`nomic-embed-text`, 768 dimensions) for the vector index (`rag/vectors.py`), fused with BM25 and n-gram search.

## 3. What AI never does at run time
Code, not a model, decides: train search, seats, fares, refund amounts, deadlines, booking status, who may see what, and every change (propose, separate Confirm, execute, verify). Safety, privacy and hand-over routing is plain pattern code. The model never chooses a number and never changes a booking.

## 4. Checks on every answer
Number verifier, citation check, promise detector, privacy check and language check (`assistant/correctors.py`).

## 5. Originality
No code was copied from another team or repository; the structure follows the brief. Third-party libraries are used through their normal packages (`requirements.txt`, `ui-react/package.json`).

## 6. Limits of this evaluation
The evaluations were written or run with AI assistance by the same team that built the system, so they are optimistic. Real Ollama and Docker paths were not exercised in the AI session, and vector search and the model paths were tested only with fakes.
