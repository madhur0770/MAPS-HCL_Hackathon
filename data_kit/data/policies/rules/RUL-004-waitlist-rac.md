---
doc_id: RUL-004
title: Waitlist and RAC Rules
document_type: rule
operator: Ujjwal Rail
version: "1.0"
published_at: 2026-11-01
effective_from: 2026-11-01
language: en
status: active
---

# Waitlist and RAC Rules

## 1. Purpose

This rule defines Ujjwal Rail inventory statuses, promotion order, travel rights and cancellation treatment when confirmed inventory is unavailable.

## 2. Scope

It applies to reserved classes and to each traveller independently within a booking.

## 3. Policy Conditions

### 3.1 Status definitions

- CNF: a seat or berth is allocated or guaranteed for chart allocation; travel is permitted.
- RAC: shared-seat travel is permitted; a full berth is not guaranteed.
- WL: no travel authority exists unless the traveller is promoted to RAC or CNF.
- CAN: the traveller has been cancelled.
- USED: travel has commenced or the ticket was marked used.

### 3.2 Booking against full inventory

When CNF inventory is exhausted, the system may allocate RAC up to the class quota, then WL up to the published waitlist capacity. A passenger must see the proposed status before payment. FP may omit RAC and move directly from CNF to WL. No booking is created after the relevant quota is full.

### 3.3 Promotion order

Promotion occurs only after inventory is released. Within the same train, date, class and quota, eligible travellers are ordered by original successful booking timestamp and then by system sequence. WL promotes to RAC or CNF; RAC promotes to CNF. The assistant cannot change order or promise promotion.

### 3.4 Mixed-status bookings

Travellers in one booking may hold different statuses. CNF and RAC travellers may travel; WL travellers may not board. Cancellation or promotion is recorded per traveller and does not automatically change another traveller's status except through normal inventory release.

### 3.5 Cancellation and refunds

Before departure, RAC cancellation deducts INR 40 per traveller and WL cancellation deducts INR 20. Remaining WL travellers are automatically cancelled two hours before origin departure and receive the same treatment. Once promoted to CNF, RUL-003 Sections 3.3 to 3.6 apply. Partial cancellation follows RUL-003 Section 3.8.

### 3.6 Promotion limitations

Promotion is not guaranteed, cannot bypass class or quota boundaries and stops when charting closes 20 minutes before origin departure. A status display is not final until read from the booking system. Ujjwal Rail does not compensate a traveller solely because WL or RAC did not promote.

## 4. Exceptions

An operator cancellation refunds all statuses under RUL-011 Section 3.1. A status inconsistency, out-of-order promotion or traveller shown both CAN and active requires human review. Tatkal WL and RAC retain the non-refundable supplement rules in RUL-005 Section 3.4.

## 5. Related Rules

- RUL-001 Section 3.4: booking confirmation.
- RUL-002 Section 3.2: allocation conventions.
- RUL-003 Sections 3.7 and 3.8: RAC, WL and partial refunds.
- RUL-005 Sections 3.2 to 3.4: Tatkal quota and refunds.
