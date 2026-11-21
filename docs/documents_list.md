# Document ID list

38 documents: 12 rules, 6 circulars, 20 FAQs. Generated from `core/content.py` (the single source of truth for numbers and text).

| doc_id | type | topic | in force from | replaces | language | title |
|---|---|---|---|---|---|---|
| RULE-01 | rule | booking | 2026-01-01 | - | en | Booking basics |
| RULE-02 | rule | fares | 2026-01-01 | - | en | Fares |
| RULE-03 | rule | refund | 2026-01-01 | - | en | Cancellation and refund |
| RULE-04 | rule | waitlist | 2026-01-01 | - | en | Waiting list |
| RULE-05 | rule | train_cancelled | 2026-01-01 | - | en | Train cancelled by the operator |
| RULE-06 | rule | tatkal | 2026-01-01 | - | en | Tatkal (last-minute) booking |
| RULE-07 | rule | boarding_change | 2026-01-01 | - | en | Changing the boarding station |
| RULE-08 | rule | concession | 2026-01-01 | - | en | Children, seniors and concessions |
| RULE-09 | rule | luggage | 2026-01-01 | - | en | Luggage and pets |
| RULE-10 | rule | dispute | 2026-01-01 | - | en | Refund disputes and special cases |
| RULE-11 | rule | actions | 2026-01-01 | - | en | How the assistant makes changes |
| RULE-12 | rule | privacy | 2026-01-01 | - | en | Privacy and data |
| CIR-2026-05 | circular | waitlist | 2026-09-01 | RULE-04 | en | Circular: Waiting list clarification |
| CIR-2026-07 | circular | refund | 2026-11-22 | RULE-03 | en | Circular: Higher cancellation charge for 2A |
| CIR-2026-08 | circular | tatkal | 2026-11-25 | RULE-06 | en | Circular: Tatkal charge for Sleeper |
| CIR-2026-09 | circular | boarding_change | 2026-12-01 | RULE-07 | en | Circular: Boarding-station change cut-off shortened |
| CIR-2026-10 | circular | waitlist | 2026-12-15 | RULE-04 | en | Circular: Waiting list clerkage revised |
| CIR-2026-11 | circular | refund | 2026-12-20 | RULE-03 | en | Circular: Festival cancellation waiver |
| FAQ-01 | faq | refund | 2026-03-01 | - | en | How much will I get back if I cancel? |
| FAQ-02 | faq | boarding_change | 2026-03-01 | - | en | Can I change my boarding station on the day? |
| FAQ-03 | faq | tatkal | 2026-03-01 | - | en | What is the Tatkal charge? |
| FAQ-04 | faq | waitlist | 2026-03-01 | - | en | Will my waitlisted ticket get confirmed? |
| FAQ-05 | faq | concession | 2026-03-01 | - | en | Do children need a ticket? |
| FAQ-06 | faq | booking | 2026-03-01 | - | en | How do I check my booking status? |
| FAQ-07 | faq | booking | 2026-03-01 | - | en | What does RAC mean? |
| FAQ-08 | faq | luggage | 2026-03-01 | - | en | Can I take my pet? |
| FAQ-09 | faq | luggage | 2026-03-01 | - | en | How much luggage can I carry? |
| FAQ-10 | faq | train_cancelled | 2026-03-01 | - | en | My train was cancelled. Do I get a refund? |
| FAQ-11 | faq | actions | 2026-03-01 | - | en | Can the assistant cancel my ticket? |
| FAQ-12 | faq | dispute | 2026-03-01 | - | en | I missed my train. Can I get a refund? |
| FAQ-13 | faq | waitlist | 2026-03-01 | - | en | Is there a fee to cancel a waitlisted ticket? |
| FAQ-14 | faq | booking | 2026-03-01 | - | en | How early can I book? |
| FAQ-15 | faq | privacy | 2026-03-01 | - | en | Can someone else cancel my booking? |
| FAQ-16 | faq | refund | 2026-03-01 | - | hi | टिकट रद्द करने पर कितना पैसा वापस मिलेगा? |
| FAQ-17 | faq | refund | 2026-03-01 | - | hinglish | Ticket cancel karne par paisa kitna wapas milega? |
| FAQ-18 | faq | boarding_change | 2026-03-01 | - | hinglish | Boarding station kaise badlein? |
| FAQ-19 | faq | waitlist | 2026-03-01 | - | hi | वेटिंग टिकट का क्या होगा? |
| FAQ-20 | faq | concession | 2026-03-01 | - | en | Is there any discount for senior citizens? |

Deliberate traps: FAQ-02 (says 12 hours; rule says 24) and FAQ-03 (Tatkal Rs 150) / FAQ-13 (clerkage Rs 30) go out of date when CIR-2026-08 / CIR-2026-10 take effect. CIR-2026-07, -08, -09, -10, -11 are future-dated from the demo date (21 Nov 2026).
