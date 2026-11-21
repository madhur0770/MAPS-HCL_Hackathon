# Ujjwal Rail Circular Changelog

This changelog is a machine-implementation aid. The individual circular remains the authoritative amendment text.

## 1. Numerical amendments

| Circular | Setting key | Original rule | Original value | Revised value | Effective instant | Before effective instant | On or after effective instant |
|---|---|---|---|---|---|---|---|
| CIR-001 | `cancel_fixed_charge_ac2` | RUL-003 3.3 and repeated in RUL-002 3.4 | INR 240 | INR 260 | 2026-11-15 00:00 Asia/Kolkata | RUL-003 value INR 240 | CIR-001 value INR 260 |
| CIR-001 | `cancel_fixed_charge_ac3` | RUL-003 3.3 and repeated in RUL-002 3.4 | INR 200 | INR 220 | 2026-11-15 00:00 Asia/Kolkata | RUL-003 value INR 200 | CIR-001 value INR 220 |
| CIR-002 | `tatkal_supplement_ac2` | RUL-005 3.3 | INR 400 | INR 450 | 2026-11-20 00:00 Asia/Kolkata | RUL-005 value INR 400 | CIR-002 value INR 450 |
| CIR-002 | `tatkal_supplement_ac3` | RUL-005 3.3 | INR 300 | INR 330 | 2026-11-20 00:00 Asia/Kolkata | RUL-005 value INR 300 | CIR-002 value INR 330 |
| CIR-005 | `excess_luggage_rate_per_started_kg` | RUL-007 3.2 | INR 30 | INR 35 | 2027-01-01 00:00 Asia/Kolkata | RUL-007 value INR 30 | CIR-005 value INR 35 |

## 2. Applicability events

- CIR-001 selects the value by the timestamp at which a voluntary-cancellation request is accepted. Booking date and journey date do not select the value.
- CIR-002 selects the value when Tatkal payment and inventory allocation both complete. Completed earlier bookings are not repriced.
- CIR-005 selects the value when excess-luggage registration is accepted. Completed earlier registrations are not repriced.

## 3. Clarifications without amendments

### CIR-003

RUL-004 Sections 3.3 and 3.4 continue unchanged. The circular explains that inventory release occurs on committed cancellation, after which existing booking-time and sequence ordering applies per traveller. It changes no charge, quota, status right or time cutoff.

### CIR-004

RUL-010 Sections 3.2 and 3.5 continue unchanged. The circular explains that the official schedule attached to the booking controls the six-hour deadline; a forecast delay does not extend it. It changes no numerical deadline or station eligibility.

### CIR-006

RUL-012 Sections 3.3 and 3.5 continue unchanged. The circular explains that urgent safety handoff must not wait for complete booking or identity details. It changes neither the immediate-handoff requirement nor the 15-minute acknowledgement target.

## 4. Conflict check

The five amended setting keys are distinct. No circular revises the same setting twice. CIR-005 is future-effective and must remain inactive through 2026-12-31. Clarification circulars do not override values.

## 5. Generation provenance

- The circulars were authored in this Codex session from the attached user prompt and validated against the local rule files.
- No separate content-generation API or independently identified external LLM was invoked.
- The exact runtime model identifier was not exposed to the project, so no model name is asserted.
- The exact operative prompt is preserved in `data_generation/circular_generation_prompt.md`.
