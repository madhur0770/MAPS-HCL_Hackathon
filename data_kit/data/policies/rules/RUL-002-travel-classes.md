---
doc_id: RUL-002
title: Travel Classes
document_type: rule
operator: Ujjwal Rail
version: "1.0"
published_at: 2026-11-01
effective_from: 2026-11-01
language: en
status: active
---

# Travel Classes

## 1. Purpose

This rule defines Ujjwal Rail class codes, allocation conventions and the class attributes used by fare, cancellation and luggage rules.

## 2. Scope

It applies to all reserved passenger services. A train may offer only a subset of the supported classes.

## 3. Policy Conditions

### 3.1 Supported classes

| Code | Name | Allocation | Key characteristic |
|---|---|---|---|
| FP | First Premium | enclosed berth | highest privacy; limited inventory |
| AC2 | Air Comfort 2 Tier | berth | two-tier cooled sleeping accommodation |
| AC3 | Air Comfort 3 Tier | berth | three-tier cooled sleeping accommodation |
| EC | Executive Chair | reserved seat | premium daytime seating |
| SL | Sleeper | berth | non-cooled sleeping accommodation |
| CC | City Chair | reserved seat | standard daytime seating |

No other class code is valid for Ujjwal Rail policy calculations.

### 3.2 Allocation conventions

CNF means an individual seat or berth is allocated or guaranteed for allocation at charting. RAC means shared-seat travel is permitted but a berth is not guaranteed. WL does not permit boarding. Berth preference is a request only. The allocation engine may separate travellers when adjacent inventory is unavailable.

### 3.3 Class restrictions

FP inventory may be restricted to journeys longer than 200 route kilometres. EC and CC are seat-only classes and do not accept berth preferences. A class change requires cancellation and a new booking; the assistant cannot directly convert a booking between classes.

### 3.4 Fare and cancellation attributes

Base fare is stored per traveller. The fixed voluntary cancellation charges are FP INR 300, AC2 INR 240, AC3 INR 200, EC INR 220, SL INR 120 and CC INR 100. RUL-003 Section 3.4 determines when these amounts or percentage deductions apply.

### 3.5 Luggage and Tatkal attributes

Free luggage allowances are FP 70 kg, AC2 50 kg, AC3 40 kg, EC 35 kg, SL 30 kg and CC 25 kg under RUL-007 Section 3.1. Tatkal supplements are defined in RUL-005 Section 3.3.

## 4. Exceptions

An equipment substitution may change a seat or berth number but may not silently lower the booked class. A forced downgrade requires human review and a fare-difference refund. Accessibility assistance does not create an entitlement to a particular berth unless the allocation system confirms it.

## 5. Related Rules

- RUL-001 Sections 3.3 to 3.5: booking limits and confirmation.
- RUL-003 Sections 3.3 to 3.7: class-based cancellation calculation.
- RUL-004 Section 3.1: booking statuses.
- RUL-005 Section 3.3: Tatkal supplements.
- RUL-007 Section 3.1: luggage allowances.

