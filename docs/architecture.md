# Architecture

```
Browser (Streamlit)  --->  FastAPI  --->  assistant.router.handle()
                              |                 |
   X-Passenger-Id header      |      1 input guard   (mask PII, secrets, injection)
   rate limit, size limit     |      2 understand    (rules in en/hi/hinglish; optional LLM suggestion)
   JSON logs, request id      |      3 context       (session memory, relative dates, station aliases)
                              |      4 route         (answer | tool | action | handoff | clarify | refuse)
                              |      5 execute       (tools/*  rag/*  actions/*)
                              |      6 compose       (templates in 3 languages, numbers from code)
                              |      7 correctors    (numbers, citations, promises, privacy, language)
                              |      8 output guard  (mask phone / ID)
                              |      9 audit record  (GET /trace/{id})
                              v
                 SQLite (stations, trains, train_stops, fares, seats, passengers, bookings,
                         booking_travellers, actions, settings + settings_history, documents,
                         sessions, handoffs, audit)
```

**Why plain Python and not an agent framework.** One request is a fixed path with a few branches; code is easier to test, faster, and every line can be explained.
The "roles" (router, retrieval, tools, action manager, handoff, corrector) are modules, not separate model agents.

**Changes (levels).** 0 lookups run directly. 1 own-booking changes (cancel, change boarding, book) are previewed, then need a separate Confirm call,
run in one database transaction, and are verified by re-reading. 2 decisions for staff (refund disputes, missed train, concessions needing proof) become a handoff with a summary and no promise.
3 never: refunds above the rule, waiting-list jumps, fare changes, acting on someone else's booking.

**Documents and dates.** Every document has a type, an in-force date and what it replaces. The answer for a date uses only documents in force then;
a circular beats the rule it replaces, rules beat FAQs, newer beats older. A future circular is mentioned as "takes effect on ...". Numbers live in `settings_history` with effective dates.

**Live ingest.** `POST /ingest` adds a document, removes instruction-like sentences, reads numbers into `settings_history` (shown back for checking, or sent explicitly), rebuilds the index. No restart.

**Clock.** `as_of` in a request (or `DEMO_NOW`) sets "now" for that question. A preview remembers its clock offset so confirming it later uses the same timeline; if the refund would differ at confirm time, nothing happens and a fresh preview is issued.

**Failure behaviour.** Model off or slow: rules and templates still answer. Any exception in a handler: a safe message, nothing half-changed (transactions roll back). A corrector failure: one fallback to the plain extract, else a safe template.
