# Task: Generate 6 Ujjwal Rail Policy Circulars

## 1. Project location

The existing project directory is:

`~/Desktop/HCL_Hackathon`

Work exclusively inside this directory.

Before generating anything:

1. Verify that the directory exists.
2. Inspect the existing project structure.
3. Read all 12 rule documents in `data/policies/rules/`.
4. Read `RULE_INDEX.md` and `POLICY_ASSUMPTIONS.md`.
5. Extract the actual rules, numerical values, deadlines, effective dates and section references.

**IMPORTANT:** The existing rule documents are the authoritative baseline. Do not invent their contents or assume values from previous prompts.

Do not modify or regenerate the existing 12 rule documents.

## 2. Project context

We are developing an AI-Powered Train Travel Assistant for the fictional railway operator Ujjwal Rail as part of the HCLTech Future Ready AI Engineer Hackathon.

We have already generated 12 synthetic railway rule documents.

We now need to generate exactly **6 policy circulars**, as required by Section 4.1 of the hackathon problem statement.

These circulars will eventually be ingested into a RAG system and used by a policy precedence resolver.

The assistant must distinguish between original rules, amendments, future-effective policies and outdated information.

## 3. Scope

Generate ONLY:

- 6 policy circular documents.
- A circular index.
- A circular change summary.
- A record of the generation prompt.

Do NOT generate:

- Additional rule documents.
- FAQs or helpdesk replies.
- SQLite databases or settings tables.
- Train schedules, bookings or passenger data.
- FastAPI endpoints.
- RAG or vector database implementations.
- Frontend code.

Do not modify unrelated existing files.

## 4. Required directory structure

Create:

```text
~/Desktop/HCL_Hackathon/
├── data/
│   └── policies/
│       ├── rules/              # Existing: do not modify
│       └── circulars/
│           ├── CIR-001.md
│           ├── CIR-002.md
│           ├── CIR-003.md
│           ├── CIR-004.md
│           ├── CIR-005.md
│           ├── CIR-006.md
│           ├── CIRCULAR_INDEX.md
│           └── CIRCULAR_CHANGELOG.md
└── data_generation/
    └── circular_generation_prompt.md
```

## 5. Circular requirements

Generate exactly 6 realistic, original Ujjwal Rail circulars.

At least **2 circulars must explicitly override or amend earlier rule documents**.

At least **1 circular must have a future effective date**.

I recommend the following distribution, but adapt it to the actual existing rules.

### CIR-001 — Revised Cancellation Charges

- Amend a specific provision of the existing cancellation/refund rule.
- Identify the exact original rule ID and section.
- Change at least one numerical cancellation charge.
- State the previous value and revised value.
- Specify the effective date.
- Explain which bookings or cancellation requests are affected.
- Ensure the revised value can be implemented deterministically.

### CIR-002 — Revised Tatkal Charges or Booking Window

- Amend a specific provision of the existing Tatkal rule.
- Change a numerical charge, deadline or booking window.
- Identify the exact original rule ID and section.
- State the old and new values.
- Define the effective date and applicability.

### CIR-003 — Waitlist/RAC Operational Clarification

- Clarify an existing waitlist or RAC provision.
- Reference the exact existing rule and section.
- Explain a specific operational edge case.
- Avoid changing unrelated numerical values.
- This circular may be written in Hindi or Hinglish.

### CIR-004 — Boarding Station Change Clarification

- Clarify or amend an existing boarding station change provision.
- Reference the original rule and section.
- Define applicability and any exceptions.
- Ensure the circular does not contradict other active policies.

### CIR-005 — Future-Effective Policy Change

- Introduce a change to an existing rule that takes effect on **2027-01-01**, which is in the future relative to the hackathon date of 2026-11-21.
- Prefer luggage allowance, boarding-change rules or another suitable topic supported by the existing documents.
- State the existing value and future value.
- Clearly specify that the original rule remains applicable before the effective date.
- Ensure that this circular does not override any other rule prematurely.

### CIR-006 — Passenger Guidance or Complaint Procedure Update

- Provide an operational clarification or revised passenger guidance.
- Reference an existing rule document and section.
- Include a realistic example or clarification.
- This circular may be written in Hindi or Hinglish.

You may adjust the topics if necessary to remain consistent with the existing rules.

## 6. Document format

Use Markdown with YAML front matter, consistent with the existing rule documents.

Example:

```markdown
---
doc_id: CIR-001
title: Revised Cancellation Charges
document_type: circular
operator: Ujjwal Rail
version: "1.0"
published_at: 2026-11-10
effective_from: 2026-11-15
language: en
status: active
references:
  - doc_id: RUL-003
    section: "3.1"
change_type: amendment
---

# Revised Cancellation Charges

## 1. Purpose

## 2. Reference to Existing Rule

## 3. Amendment Details

## 4. Effective Date and Applicability

## 5. Examples

## 6. Unchanged Provisions
```

The metadata schema should remain consistent across all 6 circulars.

Use exact document IDs and section numbers taken from the existing rule files.

Do not reference nonexistent sections.

## 7. Policy precedence requirements

The circulars must support the following behavior:

**Before a circular becomes effective:**
- The original rule remains applicable.

**On or after its effective date:**
- The amended provision takes precedence over the original rule.

**Unchanged provisions:**
- Continue to follow the original rule.

**Future-effective circulars:**
- Must not affect present-day calculations until their effective date.

**Clarification circulars:**
- Must not silently change numerical values or eligibility conditions.

Avoid ambiguous amendment language such as "charges may be revised" or "new rules apply soon."

Use explicit values, conditions, dates and affected sections.

Where relevant, specify whether applicability depends on the booking creation date, cancellation request date, journey date or another event. Do not leave this implicit.

## 8. Machine-readable change information

For every circular that changes a numerical value, include a structured amendment table.

Example:

| Field | Value |
|---|---|
| Original rule | RUL-003 |
| Original section | 3.1 |
| Setting key | cancel_charge_2AC_over_48h |
| Previous value | Read from existing rule |
| Revised value | Newly invented value |
| Effective date | 2026-11-15 |
| Applicability | Cancellation requests submitted on or after the effective date |

The setting key must be stable and suitable for future use in the SQLite settings table.

Do not create the settings table yet.

## 9. Multilingual requirements

At least 2 circulars should contain Hindi or Roman-script Hinglish content.

For consistency:

- Keep document IDs and metadata keys in English.
- Preserve numerical values and dates exactly across languages.
- Use natural, passenger-friendly Hindi or Hinglish.
- Avoid changing the meaning during translation.
- Include an English summary for every Hindi/Hinglish circular to support review.

## 10. Consistency and validation

After generating the circulars, verify:

1. Exactly 6 circular documents exist.
2. Every circular has a unique ID.
3. Every circular has valid metadata.
4. At least 2 circulars explicitly amend earlier rules.
5. At least 1 circular takes effect after 2026-11-21.
6. Every referenced rule document exists.
7. Every referenced section exists.
8. Every numerical amendment includes previous and revised values.
9. Previous values match the actual existing rules.
10. No circular accidentally changes unrelated provisions.
11. Effective dates are valid and unambiguous.
12. No two circulars create unresolved contradictory amendments.
13. Hindi/Hinglish circulars preserve the intended meaning.
14. Original rule documents remain unchanged.
15. All content concerns fictional Ujjwal Rail policies.

If a proposed circular conflicts with existing rules in an unintended way, revise the circular rather than modifying the original rule.

## 11. Additional deliverables

### CIRCULAR_INDEX.md

Create a table containing:

- Circular ID
- Title
- Referenced rule
- Amendment or clarification
- Publication date
- Effective date
- Language
- Status as of 2026-11-21

### CIRCULAR_CHANGELOG.md

Create a summary of all amendments.

For each amendment, document:

- Original rule and section
- Original value or condition
- Revised value or condition
- Effective date
- Which rule applies before the effective date
- Which rule applies on or after the effective date

This document will later help us implement policy precedence and numerical settings.

### circular_generation_prompt.md

Preserve this exact prompt and record the model used, if available.

Do not fabricate generation provenance.

## 12. Execution instructions

1. Verify the project directory.
2. Read all existing rule documents and policy assumptions.
3. Identify suitable provisions for amendment.
4. Generate 6 circulars.
5. Ensure at least 2 explicit rule changes.
6. Ensure at least 1 future-effective circular.
7. Include Hindi/Hinglish content.
8. Create the circular index and changelog.
9. Perform consistency checks against the original rules.
10. Report all generated files and the exact changes introduced.

Do not stop after proposing a design.

**Generate all 6 circulars now, without modifying the existing rules.**