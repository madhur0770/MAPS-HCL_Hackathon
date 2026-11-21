---
doc_id: RUL-003
title: Cancellation and Refund Rules
document_type: rule
operator: Ujjwal Rail
version: "1.0"
published_at: 2026-11-01
effective_from: 2026-11-01
language: en
status: active
---

# Cancellation and Refund Rules

## 1. Purpose

This rule defines deterministic voluntary-cancellation eligibility, deductions and refund calculations for Ujjwal Rail bookings.

## 2. Scope

It applies to passenger-requested cancellation. Operator cancellation and qualifying delays use RUL-011 and override this rule. Tatkal restrictions in RUL-005 Section 3.4 also apply.

## 3. Policy Conditions

### 3.1 Eligibility by booking status

CNF, RAC and WL travellers may be cancelled before their recorded boarding-station departure. CAN and USED travellers cannot be cancelled again. At or after departure, voluntary cancellation receives no refund. A cancellation is complete only when the booking system records CAN status.

### 3.2 Fare components

For each traveller, `total_paid` consists of base fare, taxes, service fee, Tatkal supplement and recorded add-ons. Percentage deductions apply only to the base fare actually paid after concession. Service fees and Tatkal supplements are non-refundable on voluntary cancellation. Unused refundable taxes are returned. Luggage and pet add-ons follow RUL-007 Section 3.4 and RUL-008 Section 3.3.

### 3.3 Fixed charges by class

| Class | FP | AC2 | AC3 | EC | SL | CC |
|---|---:|---:|---:|---:|---:|---:|
| Fixed charge | INR 300 | INR 240 | INR 200 | INR 220 | INR 120 | INR 100 |

### 3.4 Complete CNF cancellation table

Let `t` be the exact duration between accepted cancellation time and scheduled departure from the recorded boarding station.

| Band | Exact interval | Deduction from base fare |
|---|---|---|
| A | `t > 48 hours` | applicable class fixed charge |
| B | `12 hours < t <= 48 hours` | greater of 25% of base fare or class fixed charge |
| C | `4 hours < t <= 12 hours` | greater of 50% of base fare or class fixed charge |
| D | `0 < t <= 4 hours` | greater of 75% of base fare or class fixed charge |
| E | `t <= 0` | 100% of base fare; no voluntary refund |

These intervals are exhaustive and do not overlap.

### 3.5 Boundary examples

- Exactly 48 hours before departure is Band B. One minute later, with 47 hours 59 minutes remaining, is also Band B.
- Exactly 12 hours before departure is Band C. One minute later, with 11 hours 59 minutes remaining, is also Band C.
- Exactly 4 hours before departure is Band D. One minute later, with 3 hours 59 minutes remaining, is also Band D.

### 3.6 Calculation and rounding

For a CNF traveller before departure:

1. Select the band using Section 3.4.
2. Calculate the percentage amount on discounted base fare when the band requires it.
3. Round that amount upward to the next INR 5.
4. Use the greater of the rounded percentage amount and the class fixed charge.
5. Calculate `refund = max(0, base fare - deduction) + refundable taxes + refundable add-ons`.
6. Round the final refund downward to the nearest whole INR.

A deduction can never create a negative refund. Non-refundable service fees and supplements are excluded before the calculation.

### 3.7 RAC and WL cancellation

Before departure, a cancelled RAC traveller is charged INR 40 and a cancelled WL traveller INR 20. These status charges replace, rather than add to, the CNF table. Remaining WL travellers are automatically cancelled two hours before origin departure with the INR 20 charge. If RAC or WL becomes CNF before cancellation is accepted, the CNF table applies.

### 3.8 Mixed status and partial cancellation

Each traveller is evaluated independently using their status at the accepted cancellation timestamp. Cancelling one traveller does not cancel others. Shared fees allocated at booking are apportioned equally, with the final traveller receiving any one-rupee remainder. Cancelling a lead traveller does not invalidate remaining travellers, but contact details must be replaced when required.

### 3.9 Processing timelines

Card and wallet refunds are initiated within five business days after successful cancellation. Approved cash-counter refunds are available within two business days. Banking settlement time is outside Ujjwal Rail's promise. A missing or mismatched fare component, duplicate debit, negative computed result or disputed status requires human review.

## 4. Exceptions

No voluntary refund is due for a USED traveller, a request accepted at or after departure, or a CNF Tatkal traveller under RUL-005 Section 3.4. Operator cancellation and delays use RUL-011 Sections 3.1 to 3.4 and may refund otherwise non-refundable components.

## 5. Related Rules

- RUL-002 Section 3.4: class charges.
- RUL-004 Sections 3.1 to 3.5: RAC, WL and promotion.
- RUL-005 Section 3.4: Tatkal refunds.
- RUL-009 Section 3.5: discounted-ticket refunds.
- RUL-011 Sections 3.1 to 3.4: operator disruption refunds.

