# Submission checklist (brief section 8)

Every required item, where it is, and how to check it. Tag: `final`.

| # | Required | Where | How to check |
|---|---|---|---|
| 1 | Git repository with a README, tagged as final | repository root, `README.md`, tag `final` | `git tag --list final`; `git status` must be clean |
| 2 | `docker compose up` starts the API, the interface and the database | `docker-compose.yml`, `Dockerfile` | `docker compose up --build`, then open http://localhost:8000 (React UI + API) or http://localhost:8501 (Streamlit). The database is a SQLite file in the named volume `appdata`; it is created on first start and kept on restart. `GET /health` returns 200 |
| 3 | Rules, circulars and FAQs, with a list of document IDs | `data_kit/data/policies/{rules,circulars,faqs}`; list in `docs/documents_list.md` (38 documents) | `GET /sources` returns the same list from the running system |
| 4 | Data kit: prompts, generator script, checking script | prompts `data_kit/data_generation/*.md`; generator `data_kit/scripts/generate_railway_data.py` (+ `seed_*.py`); checkers `data_kit/scripts/validate_railway_data.py`, `validate_settings.py`, `scripts/validate_data.py`; kit tests `python scripts/run_kit_tests.py` | `python data_kit/scripts/validate_railway_data.py` (32 checks), `python scripts/run_kit_tests.py` (21 tests) |
| 5 | Evaluation set and results (section 7) | set: `eval/ujjwal_rail_evaluation_40.csv` (40 questions, with `eval/questions.jsonl` 66 more); results: `eval/report_40.md`, `eval/results_40.csv`, `eval/report.md`; supplemental robustness: `eval/report_robust.md` | `python scripts/run_csv_eval.py` rewrites the report from a real run |
| 6 | Three sample audit records, one cancellation through preview, confirm, change, check | `docs/audit_samples/sample1_full_cancel_flow.json` (estimate, preview, booking before, confirm, booking after, both traces), `sample2_handoff_missed_train.json`, `sample3_injection_and_privacy.json` | `python scripts/make_audit_samples.py` regenerates them |
| 7 | Note on which parts were written with AI tools | `docs/ai_use.md` | |
| 8 | Short statement of who on the team built what | `docs/team_and_declarations.md` | |
| 9 | Signed declaration of original work from each team member | `docs/declarations/` (one form per member, **each member signs**) | |

One command checks the technical items: `python scripts/check_all.py` (10 steps: data, unit, API, red-team, 66-question evaluation, 40-question evaluation, robustness suite, audit samples).
