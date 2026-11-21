# Task: Generate 12 Synthetic Railway Rule Documents for Ujjwal Rail

## 1. Project location

The existing project directory is:

`~/Desktop/HCL_Hackathon`

**IMPORTANT:**
- Work exclusively inside `~/Desktop/HCL_Hackathon`.
- First verify that this directory exists and inspect its current contents.
- Do not create another `HCL_Hackathon` folder or a separate project root.
- Do not delete, overwrite or modify unrelated files.
- Create missing subdirectories as required.
- If the folder is inaccessible, report the issue rather than creating files elsewhere.

## 2. Project context

We are developing an AI-Powered Train Travel Assistant for a fictional railway operator called **Ujjwal Rail**, as part of the HCLTech Future Ready AI Engineer Hackathon.

The assistant will eventually support train searches, seat availability, bookings, cancellations, refunds, railway policy questions, multilingual conversations and human escalation.

We are currently implementing only **Section 4.1: Rules Documents** of the problem statement.

The documents will later be used by a Retrieval-Augmented Generation (RAG) system to answer passenger queries with document-level and section-level citations.

All railway policies, charges, deadlines and operational rules must be fictional and internally consistent.

Do not copy actual Indian Railways or IRCTC policies or present invented values as real railway rules.

## 3. Scope

Generate exactly **12 authoritative railway rule documents**.

Do not generate:
- Circulars
- FAQs
- Synthetic passenger records
- Train schedules
- Booking records
- SQLite databases or settings tables
- RAG implementation
- FastAPI backend
- Streamlit frontend

We will implement those separately.

## 4. Required directory structure

Create the following files:

```text
~/Desktop/HCL_Hackathon/
├── data/
│   └── policies/
│       └── rules/
│           ├── RUL-001-booking.md
│           ├── RUL-002-travel-classes.md
│           ├── RUL-003-cancellation-refunds.md
│           ├── RUL-004-waitlist-rac.md
│           ├── RUL-005-tatkal.md
│           ├── RUL-006-identity-verification.md
│           ├── RUL-007-luggage.md
│           ├── RUL-008-pets.md
│           ├── RUL-009-concessions.md
│           ├── RUL-010-boarding-changes.md
│           ├── RUL-011-train-cancellations-delays.md
│           ├── RUL-012-complaints.md
│           ├── RULE_INDEX.md
│           └── POLICY_ASSUMPTIONS.md
└── data_generation/
    └── rule_generation_prompt.md
```

## 5. Required rule documents

### RUL-001: Booking Rules
Define:
- Advance booking window
- Booking eligibility
- Maximum travellers per booking
- Booking confirmation conditions
- Booking deadlines
- Booking reference generation conventions
- Restrictions and exceptions

### RUL-002: Travel Classes
Define:
- Supported classes and class codes
- General characteristics of each class
- Seat/berth allocation conventions
- Class-specific booking restrictions
- Rules relevant to fare and cancellation calculations

### RUL-003: Cancellation and Refund Rules
This is the most important document.

Define:
- Voluntary cancellation conditions
- Cancellation eligibility by booking status
- Complete refund table covering every supported class
- Cancellation charges by time before departure
- Percentage-based and fixed cancellation charges
- Refund calculation formula
- Exact cutoff boundary conditions
- Rounding conventions
- No-refund conditions
- RAC and waitlisted ticket cancellation
- Mixed-status bookings
- Partial cancellation policy
- Refund processing timelines
- Exceptions and human escalation

Use explicit, non-overlapping time intervals.

Include boundary examples for:
- Exactly 48 hours before departure
- One minute after the 48-hour cutoff
- Exactly 12 hours before departure
- One minute after the 12-hour cutoff
- Exactly 4 hours before departure
- One minute after the 4-hour cutoff

Specify whether refund percentages apply to the base fare or the total amount paid.

Ensure cancellation charges never produce a negative refund.

### RUL-004: Waitlist and RAC Rules
Define:
- CNF, RAC and WL statuses
- Seat availability and status transitions
- Rules for booking against full inventory
- Cancellation behavior
- Mixed-status booking behavior
- Refund eligibility
- Any limitations of automatic RAC/WL promotion

### RUL-005: Tatkal Booking Rules
Define:
- Tatkal eligibility
- Booking opening time
- Booking cutoff
- Supported classes
- Class-specific Tatkal charges
- Cancellation and refund restrictions
- Exceptions

### RUL-006: Identity Verification
Define:
- Accepted identification categories
- Requirements during booking and travel
- Identity verification failures
- Rules for minors
- Privacy and data handling restrictions

Use fictional examples only. Do not include real identity numbers.

### RUL-007: Luggage Rules
Define:
- Free luggage allowances by class
- Excess luggage limits
- Additional charges
- Restricted items
- Exceptions and complaint procedures

### RUL-008: Pet Travel Rules
Define:
- Permitted animals
- Eligible travel classes
- Advance registration requirements
- Charges
- Safety restrictions
- Required documentation
- Exceptions

### RUL-009: Passenger Concessions
Define:
- Eligible concession categories
- Discount percentages
- Applicable classes
- Required verification
- Exclusions
- Whether concessions apply to Tatkal
- Refund treatment for discounted tickets

### RUL-010: Boarding Station Changes
Define:
- Eligibility
- Allowed number of changes
- Deadline before departure
- Valid station selection
- Restrictions
- Confirmation requirements
- Failure and exception cases

### RUL-011: Operator Cancellation and Train Delays
Define:
- Full-refund conditions when Ujjwal Rail cancels a train
- Refund eligibility for significantly delayed trains
- Exact delay thresholds
- Deadline for submitting claims
- Differences from voluntary cancellation
- Cases requiring human review

### RUL-012: Complaints and Grievances
Define:
- Complaint categories
- Refund disputes
- Booking issues
- Safety and harassment complaints
- Escalation conditions
- Human handoff requirements
- Response timelines
- Restrictions on promising resolutions

## 6. Document format

Use **Markdown with YAML front matter**.

Every document must follow this structure:

```markdown
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

## 2. Scope

## 3. Policy Conditions

### 3.1 Specific Condition

### 3.2 Specific Condition

## 4. Exceptions

## 5. Related Rules
```

Use stable section numbering throughout.

Each policy statement should be sufficiently specific for a RAG assistant to answer questions without inventing missing information.

Cross-reference related documents by their exact IDs and section numbers.

## 7. Canonical policy assumptions

Before generating the documents, establish a consistent set of fictional policy values.

These should include:
- Supported travel classes
- Advance booking window
- Maximum travellers per booking
- Cancellation time cutoffs
- Cancellation charges by class
- Percentage-based refund deductions
- RAC and WL cancellation rules
- Tatkal charges
- Boarding-change deadlines
- Delay thresholds
- Refund processing timelines
- Luggage allowances and charges
- Concession percentages

Use these values consistently across all 12 documents.

Do not independently invent conflicting numbers in different documents.

Record all important decisions in:

`data/policies/rules/POLICY_ASSUMPTIONS.md`

Use a common baseline effective date of `2026-11-01`, unless a specific reason requires otherwise.

We will add future-effective circulars and overrides in a later phase. Do not create them now.

## 8. Important design requirements

The policies must be:

**Deterministic:** All numerical calculations and eligibility decisions should be implementable using Python functions.

**Unambiguous:** Deadlines, refund intervals and eligibility conditions must have explicit boundaries.

**Consistent:** No two authoritative rule documents should contradict each other.

**Traceable:** Every important rule must be identifiable using its document ID and section number.

**Extensible:** Future circulars should be able to override specific policy sections or numerical values without rewriting the original documents.

**Realistic:** The documents should resemble actual railway operating policies while using invented Ujjwal Rail values.

**Safe:** Privacy-sensitive actions, disputed refunds and safety incidents should have clear escalation rules.

Do not invent actual passenger names, phone numbers, ID numbers or booking references.

## 9. Additional deliverables

### RULE_INDEX.md

Create an index containing:
- Document ID
- Document title
- Covered topics
- Effective date
- Related documents

### POLICY_ASSUMPTIONS.md

Document:
- All important numerical values
- Refund cutoff conventions
- Supported booking statuses
- Partial cancellation decisions
- RAC/WL handling assumptions
- Date and timezone conventions
- Monetary rounding rules
- Any deliberately simplified railway behavior

### rule_generation_prompt.md

Preserve the exact prompt used to generate the rules.

Record the model actually used if available. Do not invent model provenance.

## 10. Quality validation

After generating the documents, perform a consistency review.

Verify:

1. Exactly 12 rule documents exist.
2. All 12 required topics are covered.
3. Every document has a unique ID.
4. All required metadata fields are present.
5. Every document has numbered sections.
6. All cross-document references point to valid documents and sections.
7. Cancellation tables cover all supported classes.
8. Cancellation intervals have no gaps or overlaps.
9. Exact cutoff boundaries are clearly defined.
10. Numerical values are consistent across documents.
11. Refund calculations cannot produce negative amounts.
12. Rules for CNF, RAC and WL are consistent.
13. Operator cancellations are distinguished from voluntary cancellations.
14. All rules are fictional Ujjwal Rail policies.
15. No real personal information is present.

Correct any inconsistencies found.

## 11. Execution instructions

1. Verify `~/Desktop/HCL_Hackathon` exists.
2. Inspect its current contents.
3. Establish canonical policy assumptions.
4. Create the 12 Markdown rule documents.
5. Create RULE_INDEX.md.
6. Create POLICY_ASSUMPTIONS.md.
7. Preserve the generation prompt.
8. Review all documents for consistency.
9. Report the generated file paths, key policy values and any unresolved ambiguities.

Do not stop after proposing a design.

**Generate all 12 rule documents now.**

Do not implement anything outside the specified scope.