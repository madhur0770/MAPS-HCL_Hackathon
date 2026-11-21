# Data note (one page)

**What it is.** Fictional operator "Ujjwal Rail". All names, trains, fares, rules and passengers are invented. No real person, phone or ID is used.
Phone numbers are stored only as the last 4 digits.

**How it is made.** `python scripts/generate_data.py` (fixed seed 42, "today" = 21 Nov 2026, change with `DATA_ANCHOR`). No language model is involved.
`python scripts/validate_data.py` runs 41 checks (counts from the brief, links between tables, fares add up, rule text matches the settings table).

| Item | Count | Notes |
|---|---|---|
| Stations | 15 | with other names (Bombay, CST, VT, Banaras, Madras, पुणे ...) |
| Trains | 25 | 13 forward + 12 return; one starts 23:50; one boarding stop at 00:30 next day (12301 at Kalyan) |
| Seats | 14 days per train and class | cases: available, only RAC, full with waiting list, nearly full |
| Passengers | 25 | English, Hindi and Hinglish speakers |
| Bookings | 50 | confirmed, RAC, waitlisted, cancelled, train_cancelled; some Tatkal; some with children and seniors |
| Documents | 38 | 12 rules, 6 circulars (5 future-dated, 5 replace an earlier rule), 20 FAQs (3 out of date, 4 in Hindi/Hinglish) |
| Settings | name, value, source_doc | plus `settings_history` with effective dates so any date can be answered |

**Pinned values used in tests.** BK1001: 3A Pune to Nagpur, fare Rs 2040, departs Pune 24 Nov 2026 18:00. 12123 Pune to Nagpur fares: SL 770, 3A 2040, 2A 2900, 1A 4900.

**Built-in conflicts (on purpose).** FAQ-02 says 12 hours to change boarding, RULE-07 says 24 (and CIR-2026-09 says 12 from 1 Dec 2026).
CIR-2026-07 raises the 2A cancellation charge from Rs 200 to Rs 240 from 22 Nov 2026. CIR-2026-08 raises Tatkal (Sleeper) from 150 to 175 from 25 Nov.

**Known limits.** Distances are made up (not real railway distances). Fares are km x class rate rounded to Rs 10. Seat counts are random but fixed by the seed.
