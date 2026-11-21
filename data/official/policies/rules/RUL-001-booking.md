---
doc_id: RUL-001
title: Booking Rules
document_type: rule
operator: Ujjwal Rail
version: "1.0"
published_at: 2026-11-01
effective_from: 2026-11-01
language: en
status: active
---

# Booking Rules

## 1. Purpose

This rule defines how passengers create fictional Ujjwal Rail reservations and when a reservation becomes binding.

## 2. Scope

It applies to normal and Tatkal reservations in every class listed in RUL-002 Section 3.1. It does not govern group movements of more than six travellers, charter services or staff travel.

## 3. Policy Conditions

### 3.1 Advance booking window

Normal inventory opens at 08:00 Asia/Kolkata exactly 90 calendar days before the train's scheduled departure from its origin. The origin departure date counts as day zero. Inventory cannot be reserved before opening, even when the passenger boards later.

### 3.2 Booking eligibility

A booking may be created by an authenticated passenger or an authorised counter clerk. Every traveller must have a name, age band, selected class, origin, destination and boarding station. The booking passenger must confirm that all travellers consent to the reservation. Identity requirements are in RUL-006 Sections 3.1 to 3.4.

### 3.3 Traveller limits

A normal booking may contain one to six travellers on the same train, date, class and route. A Tatkal booking may contain one to four travellers under RUL-005 Section 3.2. Larger parties require separate bookings; Ujjwal Rail does not promise adjacent allocations across booking references.

### 3.4 Confirmation and booking reference

A booking is created only after payment is recorded and every traveller receives CNF, RAC or WL status. A payment attempt without inventory allocation is not a booking. The system generates a reference consisting of `UR-` and eight decimal digits. References are identifiers, not proof of payment or identity.

### 3.5 Booking deadlines

Normal booking closes 20 minutes before scheduled departure from the train's origin. A passenger boarding downstream is subject to the same origin cutoff. Tatkal has the earlier cutoff in RUL-005 Section 3.2. A request timestamped exactly at the cutoff is rejected.

### 3.6 Restrictions

Passengers may not hold duplicate bookings for the same traveller, train and date in overlapping routes. Inventory may not be held without recorded payment. A booking cannot be transferred to another person. Fare, class and status must come from the booking system rather than a conversational response.

## 4. Exceptions

An interrupted payment with a recorded debit but no booking must be sent to payment review. Staff may not fabricate a booking reference. Accessibility assistance may be added after booking without changing inventory. Operator-cancelled services follow RUL-011, not voluntary cancellation rules.

## 5. Related Rules

- RUL-002 Section 3.1: supported classes.
- RUL-004 Sections 3.1 to 3.4: CNF, RAC and WL allocation.
- RUL-005 Section 3.2: Tatkal window and limits.
- RUL-006 Sections 3.1 to 3.4: identity verification.
- RUL-003 Sections 3.1 to 3.9: voluntary cancellation and refunds.

