# Task: Generate 20 Synthetic FAQs and Past Helpdesk Replies for Ujjwal Rail

## 1. Project location

The existing project directory is:

`~/Desktop/HCL_Hackathon`

Work exclusively inside this directory.

Before generating any files:

1. Verify that the directory exists.
2. Inspect the existing project structure.
3. Read all 12 rule documents in `data/policies/rules/`.
4. Read all 6 circulars in `data/policies/circulars/`.
5. Read `RULE_INDEX.md`, `POLICY_ASSUMPTIONS.md`, `CIRCULAR_INDEX.md` and `CIRCULAR_CHANGELOG.md`, if present.
6. Extract the actual policies, amendments, numerical values, effective dates and document references.

**IMPORTANT:** Use the existing documents as the source of truth. Do not invent conflicting policy values or assume values from previous prompts.

Do not modify the existing rules or circulars.

## 2. Project context

We are developing an AI-Powered Train Travel Assistant for the fictional railway operator Ujjwal Rail as part of the HCLTech Future Ready AI Engineer Hackathon.

We have already created:
- 12 authoritative railway rule documents.
- 6 circulars, including amendments and future-effective changes.

We now need exactly **20 synthetic FAQ answers or past helpdesk replies**.

These documents will later be indexed in a Retrieval-Augmented Generation (RAG) system.

The RAG assistant must answer passenger questions using the correct policy version, cite authoritative documents and avoid relying on outdated FAQs when newer effective circulars apply.

## 3. Scope

Generate ONLY:
- 20 FAQ or past helpdesk reply documents.
- An FAQ index.
- An outdated FAQ tracking document.
- A record of the generation prompt.

Do NOT generate:
- Additional rules or circulars.
- SQLite databases.
- Train schedules or passenger records.
- RAG implementation.
- APIs or frontend code.
- Evaluation scripts.

Do not delete, overwrite or modify unrelated existing files.

## 4. Required directory structure

Create:

```text
~/Desktop/HCL_Hackathon/
├── data/
│   └── policies/
│       ├── rules/             # Existing, do not modify
│       ├── circulars/         # Existing, do not modify
│       └── faqs/
│           ├── FAQ-001.md
│           ├── FAQ-002.md
│           ├── FAQ-003.md
│           ├── ...
│           ├── FAQ-020.md
│           ├── FAQ_INDEX.md
│           └── OUTDATED_FAQS.md
└── data_generation/
    └── faq_generation_prompt.md
```

## 5. FAQ requirements

Generate exactly 20 FAQs or past helpdesk replies.

Use the following topic distribution:

1. FAQ-001 — Advance booking window
2. FAQ-002 — Available travel classes
3. FAQ-003 — Cancellation charges
4. FAQ-004 — Refund calculation example
5. FAQ-005 — RAC ticket eligibility
6. FAQ-006 — Waitlisted ticket cancellation
7. FAQ-007 — Tatkal booking window and charges
8. FAQ-008 — Accepted identity documents
9. FAQ-009 — Luggage allowance
10. FAQ-010 — Travelling with pets
11. FAQ-011 — Passenger concessions
12. FAQ-012 — Changing the boarding station
13. FAQ-013 — Refund when Ujjwal Rail cancels a train
14. FAQ-014 — Refund when a train is heavily delayed
15. FAQ-015 — Partial cancellation of a booking
16. FAQ-016 — Mixed confirmed/RAC/waitlisted travellers
17. FAQ-017 — Refund processing time
18. FAQ-018 — Complaint submission and escalation
19. FAQ-019 — Hindi passenger question about cancellation/refunds
20. FAQ-020 — Hinglish passenger question about Tatkal, waitlist or boarding changes

You may adjust the exact questions to reflect the actual rules and circulars, but preserve broad coverage.

## 6. Mandatory outdated FAQs

At least **2 FAQs must be intentionally outdated as of 2026-11-21 because of an already-effective circular**.

Prefer:

- FAQ-003 — Original cancellation charges, superseded by a cancellation amendment.
- FAQ-007 — Original Tatkal charges or booking window, superseded by a Tatkal amendment.

However, use these only if the existing circulars actually changed those provisions and are already effective as of 2026-11-21.

If the proposed circulars are not yet effective, select other suitable already-effective amendments.

### Critical requirements for outdated FAQs

Each outdated FAQ must:

1. Have a publication date before the relevant circular's effective date.
2. State the original policy accurately as it existed at the time of publication.
3. Reference the original rule document and section.
4. Contain a policy value or condition that is now superseded.
5. Identify the superseding circular in metadata.
6. Preserve the historical answer exactly as originally written.
7. Be clearly marked as outdated in the FAQ index and tracking document.

Do not silently update outdated FAQs to match newer circulars.

Do not insert the new policy value into the historical FAQ answer itself.

The goal is to create realistic, historically correct but currently outdated helpdesk content.

If fewer than two already-effective circular amendments exist, report that the requirement cannot currently be satisfied. Do not fabricate an amendment or falsely mark an FAQ as outdated.

## 7. Document format

Use Markdown with YAML front matter, consistent with the existing policy documents.

Example:

```markdown
---
doc_id: FAQ-003
title: Cancellation Charges for Confirmed Tickets
document_type: faq
operator: Ujjwal Rail
published_at: 2026-11-05
language: en
status: outdated
source_type: historical_helpdesk_reply
references:
  - doc_id: RUL-003
    section: "3.1"
superseded_by:
  - CIR-001
---

# Cancellation Charges for Confirmed Tickets

## 1. Passenger Question

What cancellation charges apply to my confirmed ticket?

## 2. Helpdesk Answer

[Provide the historically correct answer based on
the original rule, not the revised circular.]

## 3. Original Policy Reference

RUL-003, Section 3.1
```

The above document IDs and section numbers are illustrative. Verify the actual references before writing.

For current FAQs, use `status: current` and an empty `superseded_by` list.

For outdated FAQs, use `status: outdated` and reference the actual superseding circular.

Keep all metadata keys in English.

## 8. Historical accuracy and temporal consistency

Use **2026-11-21** as the reference date for determining whether an FAQ is currently outdated.

Apply these principles:

- An FAQ published before an amendment may accurately describe the original rule.
- An already-effective circular can make that FAQ outdated.
- A future-effective circular does not make an FAQ outdated before its effective date.
- A clarification circular should not automatically make an FAQ outdated unless it materially changes the earlier answer.
- A current FAQ must reflect all applicable circulars effective by its publication date.
- A historical helpdesk reply must not contain policy information that was introduced after its publication date.

When determining policy applicability, use the dates and conditions defined in the actual circulars.

Do not assume all circulars apply based solely on publication date.

## 9. Multilingual requirements

Include at least:

- 2 FAQs in Hindi (Devanagari script).
- 2 FAQs in Hinglish (Roman-script Hindi mixed with English).

The other FAQs may be in English.

For Hindi and Hinglish FAQs:

- Use natural passenger language.
- Keep numerical charges, cutoffs and conditions consistent with the applicable policy version.
- Include an English summary in the metadata or a separate review section.
- Do not translate document IDs.
- Do not introduce policy differences through translation.

## 10. Content quality

Each FAQ should:

- Contain a realistic passenger question.
- Provide a clear and helpful answer.
- Be grounded in one or more existing rule documents or circulars.
- Cite the exact policy document IDs and section numbers.
- Avoid unsupported promises about refunds, confirmations or complaint resolution.
- Explain conditions and exceptions where relevant.
- Avoid inventing train availability, fares, booking statuses or passenger-specific information.
- Use concise, passenger-friendly wording.

For calculation-based questions, use fictional examples with explicit assumptions and verify the arithmetic.

Do not create real passenger names, phone numbers, identity numbers or booking references.

## 11. FAQ_INDEX.md

Create a table containing:

- FAQ ID
- Title
- Language
- Publication date
- Current/outdated status as of 2026-11-21
- Referenced rule or circular
- Superseding circular, if applicable

## 12. OUTDATED_FAQS.md

Create a detailed report for every outdated FAQ.

Include:

- FAQ ID
- Original publication date
- Original rule and section
- Original policy value or condition
- Superseding circular ID
- Circular effective date
- Revised policy value or condition
- Reason the FAQ is outdated
- Expected correct answer as of 2026-11-21
- Expected authoritative citation

This report is intended for later RAG evaluation and policy precedence testing.

Do not modify the historical FAQ text to make it current.

## 13. Generation provenance

Create:

`data_generation/faq_generation_prompt.md`

Preserve this exact prompt and identify the model actually used, if available.

Do not fabricate generation provenance.

## 14. Quality validation

After generating the FAQs, verify:

1. Exactly 20 FAQ documents exist.
2. Every FAQ has a unique ID.
3. Every FAQ has the required metadata.
4. Every FAQ contains a passenger question and answer.
5. Every cited rule or circular exists.
6. Every cited section exists.
7. At least 2 FAQs are genuinely outdated due to already-effective circular amendments.
8. Outdated FAQ publication dates precede the relevant amendment effective dates.
9. Historical answers match the policy applicable when published.
10. Current FAQs reflect applicable amendments.
11. Future-effective circulars do not prematurely invalidate FAQs.
12. At least 2 Hindi and 2 Hinglish FAQs exist.
13. Numerical values are consistent with the correct policy versions.
14. No real personal information appears.
15. Existing rule and circular files remain unchanged.

If inconsistencies are found, correct the generated FAQ documents and supporting indexes.

Do not change the original rules or circulars.

## 15. Execution instructions

1. Verify `~/Desktop/HCL_Hackathon`.
2. Read all existing rules and circulars.
3. Identify at least 2 suitable already-effective amendments.
4. Generate 20 FAQ documents.
5. Ensure at least 2 are historically correct but now outdated.
6. Include Hindi and Hinglish FAQs.
7. Create FAQ_INDEX.md.
8. Create OUTDATED_FAQS.md.
9. Preserve the generation prompt.
10. Validate consistency and report the results.

Do not stop after proposing a design.

**Generate all 20 FAQs now.**