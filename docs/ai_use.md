# AI use note

- **Where AI was used to build this:** the team used Claude (Anthropic) as a coding assistant to draft the code, tests, documents and this note.
  Every member must be able to explain every file; run `python scripts/check_all.py` and read the module docstrings to prepare.
- **Where AI is used at run time:** only an *optional* local model (Ollama) which (1) may suggest an intent or read place names when the rules are unsure, (2) may reword an answer made from documents and
  (3) produces embeddings for the vector index (`rag/vectors.py`, stored in SQLite, fused with BM25). Every model suggestion is validated against the database or a fixed list before use. Safety, privacy and handoff routing is plain pattern code (`assistant/handoff.py`), not a model. It never chooses a number, never decides a refund, never changes a booking.
  With `MOCK_LLM=true` (default) the system runs with no model at all and all evaluation results are produced that way.
- **What code decides:** train search, seats, fares, refund amounts, deadlines, booking status, who can see what, and every change (propose, confirm, execute, verify).
- **Checks on every answer:** number verifier, citation check, promise detector, privacy check, language check (`assistant/correctors.py`).
- **Not copied:** no code was copied from another team or repository; the structure follows the brief only.
