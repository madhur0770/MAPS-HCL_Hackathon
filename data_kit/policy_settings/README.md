# Ujjwal Rail Policy Settings

This module stores deterministic Ujjwal Rail policy values in SQLite. The policy Markdown remains the legal source for this fictional dataset; the database is a reviewed, machine-readable projection of those documents.

## Schema

`settings` is the current snapshot required by the hackathon contract:

```sql
CREATE TABLE IF NOT EXISTS settings (
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    source_doc TEXT NOT NULL
);
```

`setting_versions` stores effective-dated history, value type, unit, precedence and applicability event. Its validity intervals are half-open: `effective_from` is included and `effective_until` is excluded.

The value is always stored as text in a machine-readable representation. Monetary values and percentages must be parsed with `Decimal`, never binary floating point.

## Initialize and seed

Run commands from the project root:

```bash
python3 scripts/init_settings.py
python3 scripts/seed_settings.py
python3 scripts/validate_settings.py
python3 -m unittest discover -s tests -v
```

The default database is `data/ujjwal_rail.db`. Each script accepts `--db PATH`. Seeding also accepts an ISO `--as-of` time for a reproducible `settings` snapshot:

```bash
python3 scripts/seed_settings.py --as-of 2026-11-21T12:00:00+05:30
python3 scripts/validate_settings.py --as-of 2026-11-21T12:00:00+05:30
```

Initialization and seeding are repeatable. Seeding upserts reviewed versions and replaces only the managed names in the current snapshot.

## Retrieve settings in Python

```python
from policy_settings import (
    get_setting,
    get_setting_decimal,
    get_setting_int,
    list_settings,
)

current = get_setting("cancel_fixed_charge_ac2")
historical = get_setting("cancel_fixed_charge_ac2", "2026-11-14")
amount, source = get_setting_decimal(
    "tatkal_supplement_ac3", "2026-11-21"
)
expiry, source = get_setting_int("actions.pending_expiry_minutes")
all_current = list_settings()
```

`get_setting` returns a `PolicySetting` containing the value, source document, validity interval, applicability event, value type and unit. Typed accessors return `(value, source_doc)`. Unknown and ambiguous settings raise explicit exceptions.

## Circular precedence

The baseline values begin on 2026-11-01. Effective circulars close the earlier version at their effective instant and begin a new version:

- CIR-001 changes AC2 and AC3 fixed cancellation charges on 2026-11-15. The event is `cancellation_request_accepted`.
- CIR-002 changes AC2 and AC3 Tatkal supplements on 2026-11-20. The event is `tatkal_booking_completed`.
- CIR-005 changes the excess-luggage rate on 2027-01-01. The event is `excess_luggage_registration_accepted`.

The future CIR-005 row is present in `setting_versions`, but the current `settings` snapshot continues to use RUL-007 until its effective instant. Clarification circulars do not create numerical versions.

## Reviewed mapping strategy

`seed_data.py` contains explicit reviewed mappings. Each policy setting identifies a source document and one or more evidence snippets. Seeding reads the current policy documents and fails if that evidence no longer matches. It does not use FAQs and does not guess numbers through general Markdown pattern matching.

## Application settings

The policy corpus does not define how long a proposed action remains open. Therefore:

```text
actions.pending_expiry_minutes = 10
source_doc = SYSTEM-CONFIG
```

This is an application default, not a Ujjwal Rail policy or invented rule citation.

## Manual review

No ambiguous numerical values were found in the current source documents. The action-expiry default is deliberately separated from policy. If source wording changes, evidence validation will stop seeding and identify the mapping that requires review.
