---
doc_id: RUL-006
title: Identity Verification
document_type: rule
operator: Ujjwal Rail
version: "1.0"
published_at: 2026-11-01
effective_from: 2026-11-01
language: en
status: active
---

# Identity Verification

## 1. Purpose

This rule defines identity evidence and privacy controls for Ujjwal Rail bookings and travel.

## 2. Scope

It applies to booking holders and travellers. All examples and categories are fictional and do not prescribe any real-government identifier.

## 3. Policy Conditions

### 3.1 Accepted categories

An adult may present one current document from an approved category: government photo identity, educational-institution photo card, employer photo card, or Ujjwal Rail verified passenger credential. The verification system stores the category, issuer label and only the last four characters of the identifier. Full identifiers must not appear in chat, logs or audit summaries.

### 3.2 Booking requirements

Normal booking requires traveller names and age bands but does not require entering a full identity number. Tatkal requires the booking passenger to select an accepted category for each adult before payment. Identity documents are not uploaded through the conversational assistant.

### 3.3 Travel requirements

At least one adult on a booking must present an accepted original or verifiable digital credential. A traveller receiving a concession must also meet RUL-009 Section 3.3. The name must substantially match the booking; minor spacing or transliteration differences may be reviewed by authorised staff.

### 3.4 Minors

A traveller under 16 may travel without separate photo identification when accompanied by a verified adult on the same booking. An unaccompanied minor requires an approved youth credential and prior human authorisation. The assistant must not decide guardianship disputes.

### 3.5 Verification failure

The assistant may explain requirements but cannot mark identity as verified. A material mismatch is referred to authorised station staff. Staff may deny boarding after review; the assistant must not promise either travel or a refund. Voluntary refund eligibility remains governed by RUL-003.

### 3.6 Privacy and access

Only the authenticated passenger may access their booking. Never reveal whether another person's booking exists. Do not repeat full identifiers, secrets or document images. Verification data is used only for travel, fraud prevention and required audit. Suspected exposure is escalated as a privacy incident under RUL-012 Section 3.4.

## 4. Exceptions

An accessibility need does not remove identity requirements, but staff may use an alternative documented verification process. A system outage or disputed match requires human review and must not be treated as automatic failure.

## 5. Related Rules

- RUL-001 Section 3.2: booking eligibility.
- RUL-005 Section 3.1: Tatkal eligibility.
- RUL-009 Section 3.3: concession verification.
- RUL-012 Sections 3.3 and 3.4: safety and privacy escalation.

