---
doc_id: RUL-010
title: Boarding Station Changes
document_type: rule
operator: Ujjwal Rail
version: "1.0"
published_at: 2026-11-01
effective_from: 2026-11-01
language: en
status: active
---

# Boarding Station Changes

## 1. Purpose

This rule defines when a passenger may move the recorded boarding station without changing the booked destination.

## 2. Scope

It applies to active CNF and RAC travellers. It does not apply to WL, CAN or USED travellers.

## 3. Policy Conditions

### 3.1 Eligibility and number of changes

The authenticated booking holder may request one boarding-station change per booking. All active travellers on the booking move to the same new boarding station. A second change requires human review and is not guaranteed.

### 3.2 Deadline

The request must be confirmed more than six hours before scheduled departure from the train's origin. Exactly six hours before origin departure is too late. The confirmation timestamp, not the initial chat request, determines eligibility.

### 3.3 Valid station selection

The new station must be a scheduled stop after the original boarding station and before the booked destination on the same train and date. Moving to an earlier station, beyond the destination, or to another route is prohibited. The destination cannot be changed through this process.

### 3.4 Fare and allocation

No fare reduction is paid when moving to a later station. The original seat or berth is retained when operationally possible. Ujjwal Rail may release the unused segment before the new station. The passenger has no travel authority on that released segment.

### 3.5 Confirmation and verification

The system must preview the original and proposed station, deadline and affected travellers. A separate confirmation is required. The change succeeds only after the booking record is updated and read back. Repeating the same confirmation must not apply the change twice.

### 3.6 Failure cases

The request fails when the deadline has passed, the station is invalid, a traveller is WL, the booking has been cancelled or the train has departed. The original boarding station remains authoritative unless verification confirms the update.

## 4. Exceptions

Operator disruption may permit a special station change after human approval. A station removed from the route, inconsistent timetable or partial-booking request requires human review. The assistant must not promise approval.

## 5. Related Rules

- RUL-001 Sections 3.4 and 3.5: active booking and deadlines.
- RUL-003 Section 3.4: cancellation time measured from recorded boarding station.
- RUL-004 Sections 3.1 and 3.4: traveller status.
- RUL-011 Section 4: disruption exceptions.

