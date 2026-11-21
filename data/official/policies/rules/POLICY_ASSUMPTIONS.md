# Ujjwal Rail Policy Assumptions

This file is the numerical baseline for the fictional Ujjwal Rail rules effective 2026-11-01. It is not a description of Indian Railways or any real operator.

## 1. Time and money conventions

- All times use Asia/Kolkata and a 24-hour clock.
- A journey deadline is measured against the scheduled departure from the passenger's currently recorded boarding station.
- A calendar day runs from 00:00 through 23:59:59.
- Currency is fictional Indian rupees (INR).
- Percentage deductions are calculated on the per-passenger base fare after any concession, not on service fees, taxes, luggage charges, pet charges or Tatkal supplements.
- A monetary deduction is rounded upward to the next INR 5. The final refund is rounded downward to the nearest whole INR.
- A refund is always `max(0, refundable amount - applicable deductions)`.

## 2. Supported classes

| Code | Class | Berth or seat | Free luggage | Fixed cancellation charge | Tatkal supplement |
|---|---|---|---:|---:|---:|
| FP | First Premium | enclosed berth | 70 kg | INR 300 | INR 500 |
| AC2 | Air Comfort 2 Tier | berth | 50 kg | INR 240 | INR 400 |
| AC3 | Air Comfort 3 Tier | berth | 40 kg | INR 200 | INR 300 |
| EC | Executive Chair | reserved seat | 35 kg | INR 220 | INR 350 |
| SL | Sleeper | berth | 30 kg | INR 120 | INR 180 |
| CC | City Chair | reserved seat | 25 kg | INR 100 | INR 150 |

## 3. Booking assumptions

- Normal bookings open 90 calendar days before origin departure at 08:00.
- Normal booking closes 20 minutes before origin departure.
- A booking contains at most six travellers; Tatkal contains at most four.
- Booking statuses are CNF, RAC, WL, CAN and USED.
- Booking references use `UR-` followed by eight system-generated decimal digits.
- A booking becomes confirmed only after inventory allocation and successful payment recording.

## 4. Voluntary cancellation bands

Let `t` be the exact time remaining before scheduled departure from the recorded boarding station.

| Band | Exact interval | CNF deduction per traveller |
|---|---|---|
| A | `t > 48 hours` | class fixed charge |
| B | `12 hours < t <= 48 hours` | greater of 25% of base fare or class fixed charge |
| C | `4 hours < t <= 12 hours` | greater of 50% of base fare or class fixed charge |
| D | `0 < t <= 4 hours` | greater of 75% of base fare or class fixed charge |
| E | `t <= 0` | 100% of base fare; no voluntary refund |

- Exactly 48 hours is Band B; 48 hours minus one minute is also Band B.
- Exactly 12 hours is Band C; 12 hours minus one minute is also Band C.
- Exactly 4 hours is Band D; 4 hours minus one minute is also Band D.
- Service fees and Tatkal supplements are non-refundable for voluntary cancellation.
- Unused refundable taxes are returned. Optional add-ons are governed by their own rule documents.
- RAC cancellation before departure deducts INR 40 per cancelled traveller.
- WL cancellation before departure deducts INR 20 per cancelled traveller.
- Remaining WL travellers are automatically cancelled two hours before origin departure with the INR 20 deduction.
- Partial cancellation is calculated independently per traveller using that traveller's status and allocated fare components.

## 5. Tatkal assumptions

- Tatkal opens at 10:00 one calendar day before origin departure and closes two hours before origin departure.
- Tatkal is available in FP, AC2, AC3, EC, SL and CC, subject to a separate quota.
- Tatkal supplements are listed in Section 2 and are not concession eligible.
- A voluntarily cancelled CNF Tatkal traveller receives no base-fare or Tatkal-supplement refund; refundable taxes may be returned.
- RAC and WL Tatkal travellers follow the standard INR 40 and INR 20 status deductions before departure; the Tatkal supplement remains non-refundable.

## 6. Other numerical assumptions

- A boarding station may be changed once, no later than six hours before origin departure.
- Excess luggage is limited to 30 kg above the class allowance and costs INR 30 per started kilogram.
- Pet registration closes 24 hours before origin departure. The charge is INR 600 plus INR 20 per started kilogram; trained assistance animals travel without that charge.
- Operator cancellation returns all recorded fare components and operator-collected add-ons.
- A passenger may decline travel and claim a full refund when the forecast or actual departure delay reaches three hours.
- An operator-cancellation or qualifying-delay claim must be submitted within 72 hours after scheduled origin departure.
- Card and wallet refunds are initiated within five business days; cash-counter refunds are available within two business days after approval.

## 7. Concessions

| Category | Discount on base fare | Classes |
|---|---:|---|
| Student Mobility | 40% | AC3, SL, CC |
| Senior Wellbeing | 25% | AC2, AC3, EC, SL, CC |
| Accessible Travel | 50% | all classes |
| Service Family | 20% | AC2, AC3, EC, SL, CC |

- One concession may be used per traveller; discounts do not stack.
- Concessions do not apply to Tatkal inventory, supplements, fees, taxes or add-ons.
- Voluntary cancellation percentages apply to the discounted base fare actually paid.

## 8. Deliberate simplifications

- Ujjwal Rail has one timezone and no dynamic pricing.
- RAC means a shared seat allocation; it does not guarantee a berth.
- WL and RAC promotion is automatic and follows cancellation order, quota and original booking timestamp.
- No automatic compensation is promised for consequential loss, missed connections or unverified service impact; such cases require human review.

## 9. Generation provenance

- The documents were authored in this Codex session from the attached user prompt and then checked with deterministic local scripts.
- No separate content-generation API or independently identified external LLM was invoked.
- The exact runtime model identifier was not exposed to the workspace, so no model name is asserted.
- The exact operative prompt is preserved in `data_generation/rule_generation_prompt.md`.
