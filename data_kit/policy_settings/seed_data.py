"""Explicitly reviewed policy-to-setting mappings.

The Markdown corpus is not parsed heuristically. Each mapping names its source
file and evidence text; seeding stops if that reviewed evidence no longer
matches the policy documents.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .database import PROJECT_ROOT


BASELINE = "2026-11-01T00:00:00+05:30"
SYSTEM_BASELINE = "1970-01-01T00:00:00+05:30"


@dataclass(frozen=True)
class SettingSeed:
    name: str
    value: str
    source_doc: str
    effective_from: str
    precedence: int
    applicability_event: str
    value_type: str
    unit: str | None
    note: str
    evidence_file: str | None
    evidence: tuple[str, ...]


def _seed(
    name: str,
    value: object,
    source_doc: str,
    *,
    unit: str | None,
    event: str,
    evidence_file: str | None,
    evidence: str | tuple[str, ...],
    effective_from: str = BASELINE,
    precedence: int = 10,
    value_type: str = "integer",
    note: str = "",
) -> SettingSeed:
    snippets = (evidence,) if isinstance(evidence, str) else evidence
    return SettingSeed(
        name=name,
        value=str(value),
        source_doc=source_doc,
        effective_from=effective_from,
        precedence=precedence,
        applicability_event=event,
        value_type=value_type,
        unit=unit,
        note=note,
        evidence_file=evidence_file,
        evidence=snippets,
    )


RULES = "data/policies/rules"
CIRCULARS = "data/policies/circulars"


def reviewed_setting_seeds() -> list[SettingSeed]:
    seeds: list[SettingSeed] = []

    booking_file = f"{RULES}/RUL-001-booking.md"
    seeds.extend(
        [
            _seed("booking.advance_window_days", 90, "RUL-001", unit="days", event="booking_created", evidence_file=booking_file, evidence="exactly 90 calendar days"),
            _seed("booking.opening_time_local", "08:00", "RUL-001", unit="local_time", event="booking_created", evidence_file=booking_file, evidence="opens at 08:00 Asia/Kolkata", value_type="time"),
            _seed("booking.max_travellers", 6, "RUL-001", unit="travellers", event="booking_created", evidence_file=booking_file, evidence="one to six travellers"),
            _seed("booking.cutoff_minutes_before_origin", 20, "RUL-001", unit="minutes", event="booking_created", evidence_file=booking_file, evidence="closes 20 minutes before scheduled departure"),
            _seed("booking.reference_digits", 8, "RUL-001", unit="digits", event="booking_created", evidence_file=booking_file, evidence="eight decimal digits"),
        ]
    )

    class_file = f"{RULES}/RUL-002-travel-classes.md"
    seeds.extend(
        [
            _seed("travel.supported_class_count", 6, "RUL-002", unit="classes", event="booking_created", evidence_file=class_file, evidence=("| FP | First Premium", "| CC | City Chair")),
            _seed("travel.fp.minimum_route_km", 200, "RUL-002", unit="km", event="booking_created", evidence_file=class_file, evidence="longer than 200 route kilometres"),
        ]
    )

    cancellation_file = f"{RULES}/RUL-003-cancellation-refunds.md"
    fixed_charges = {"fp": 300, "ac2": 240, "ac3": 200, "ec": 220, "sl": 120, "cc": 100}
    for class_code, amount in fixed_charges.items():
        seeds.append(
            _seed(
                f"cancel_fixed_charge_{class_code}",
                amount,
                "RUL-003",
                unit="INR",
                event="cancellation_request_accepted",
                evidence_file=cancellation_file,
                evidence="| Fixed charge | INR 300 | INR 240 | INR 200 | INR 220 | INR 120 | INR 100 |",
                value_type="decimal",
                note="Minimum fixed deduction for a CNF traveller in applicable bands.",
            )
        )
    cancellation_values = [
        ("cancellation.band_a.lower_hours_exclusive", 48, "hours", "`t > 48 hours`"),
        ("cancellation.band_b.lower_hours_exclusive", 12, "hours", "`12 hours < t <= 48 hours`"),
        ("cancellation.band_b.upper_hours_inclusive", 48, "hours", "`12 hours < t <= 48 hours`"),
        ("cancellation.band_b.deduction_percent", 25, "percent", "25% of base fare"),
        ("cancellation.band_c.lower_hours_exclusive", 4, "hours", "`4 hours < t <= 12 hours`"),
        ("cancellation.band_c.upper_hours_inclusive", 12, "hours", "`4 hours < t <= 12 hours`"),
        ("cancellation.band_c.deduction_percent", 50, "percent", "50% of base fare"),
        ("cancellation.band_d.lower_hours_exclusive", 0, "hours", "`0 < t <= 4 hours`"),
        ("cancellation.band_d.upper_hours_inclusive", 4, "hours", "`0 < t <= 4 hours`"),
        ("cancellation.band_d.deduction_percent", 75, "percent", "75% of base fare"),
        ("cancellation.band_e.upper_hours_inclusive", 0, "hours", "`t <= 0`"),
        ("cancellation.band_e.deduction_percent", 100, "percent", "100% of base fare"),
        ("cancellation.rac.charge", 40, "INR", "RAC traveller is charged INR 40"),
        ("cancellation.waitlist.charge", 20, "INR", "WL traveller INR 20"),
        ("cancellation.waitlist.auto_cancel_hours_before_origin", 2, "hours", "automatically cancelled two hours before origin departure"),
        ("cancellation.rounding.deduction_increment", 5, "INR", "next INR 5"),
        ("cancellation.rounding.refund_increment", 1, "INR", "nearest whole INR"),
        ("refund.card_wallet.initiation_business_days", 5, "business_days", "within five business days"),
        ("refund.cash_counter.availability_business_days", 2, "business_days", "within two business days"),
    ]
    for name, value, unit, evidence in cancellation_values:
        seeds.append(_seed(name, value, "RUL-003", unit=unit, event="cancellation_request_accepted", evidence_file=cancellation_file, evidence=evidence, value_type="decimal" if unit in {"INR", "percent"} else "integer"))
    seeds.extend(
        [
            _seed("cancellation.rounding.deduction_direction", "up", "RUL-003", unit=None, event="cancellation_request_accepted", evidence_file=cancellation_file, evidence="Round that amount upward", value_type="text"),
            _seed("cancellation.rounding.refund_direction", "down", "RUL-003", unit=None, event="cancellation_request_accepted", evidence_file=cancellation_file, evidence="Round the final refund downward", value_type="text"),
            _seed("cancellation.service_fee.refund_percent", 0, "RUL-003", unit="percent", event="cancellation_request_accepted", evidence_file=cancellation_file, evidence="Service fees and Tatkal supplements are non-refundable", value_type="decimal"),
            _seed("cancellation.tatkal_supplement.refund_percent", 0, "RUL-003", unit="percent", event="cancellation_request_accepted", evidence_file=cancellation_file, evidence="Service fees and Tatkal supplements are non-refundable", value_type="decimal"),
            _seed("cancellation.refundable_tax.refund_percent", 100, "RUL-003", unit="percent", event="cancellation_request_accepted", evidence_file=cancellation_file, evidence="Unused refundable taxes are returned", value_type="decimal"),
        ]
    )

    tatkal_file = f"{RULES}/RUL-005-tatkal.md"
    seeds.extend(
        [
            _seed("tatkal.max_travellers", 4, "RUL-005", unit="travellers", event="tatkal_booking_completed", evidence_file=tatkal_file, evidence="no more than four travellers"),
            _seed("tatkal.opening_days_before_origin", 1, "RUL-005", unit="calendar_days", event="tatkal_booking_completed", evidence_file=tatkal_file, evidence="one calendar day before scheduled origin departure"),
            _seed("tatkal.opening_time_local", "10:00", "RUL-005", unit="local_time", event="tatkal_booking_completed", evidence_file=tatkal_file, evidence="Tatkal opens at 10:00 Asia/Kolkata", value_type="time"),
            _seed("tatkal.cutoff_hours_before_origin", 2, "RUL-005", unit="hours", event="tatkal_booking_completed", evidence_file=tatkal_file, evidence="closes exactly two hours before origin departure"),
            _seed("tatkal.confirmed.voluntary_base_fare_refund_percent", 0, "RUL-005", unit="percent", event="cancellation_request_accepted", evidence_file=tatkal_file, evidence="receives no base-fare or Tatkal-supplement refund", value_type="decimal"),
            _seed("tatkal.confirmed.voluntary_supplement_refund_percent", 0, "RUL-005", unit="percent", event="cancellation_request_accepted", evidence_file=tatkal_file, evidence="receives no base-fare or Tatkal-supplement refund", value_type="decimal"),
        ]
    )
    tatkal_charges = {"fp": 500, "ac2": 400, "ac3": 300, "ec": 350, "sl": 180, "cc": 150}
    for class_code, amount in tatkal_charges.items():
        seeds.append(_seed(f"tatkal_supplement_{class_code}", amount, "RUL-005", unit="INR", event="tatkal_booking_completed", evidence_file=tatkal_file, evidence="| Tatkal supplement per traveller | INR 500 | INR 400 | INR 300 | INR 350 | INR 180 | INR 150 |", value_type="decimal"))

    luggage_file = f"{RULES}/RUL-007-luggage.md"
    luggage_allowances = {"fp": 70, "ac2": 50, "ac3": 40, "ec": 35, "sl": 30, "cc": 25}
    for class_code, kg in luggage_allowances.items():
        seeds.append(_seed(f"luggage.free_allowance_{class_code}_kg", kg, "RUL-007", unit="kg", event="journey", evidence_file=luggage_file, evidence="| Free allowance | 70 kg | 50 kg | 40 kg | 35 kg | 30 kg | 25 kg |"))
    seeds.extend(
        [
            _seed("luggage.maximum_excess_kg", 30, "RUL-007", unit="kg", event="excess_luggage_registration_accepted", evidence_file=luggage_file, evidence="Up to 30 kg above the class allowance"),
            _seed("excess_luggage_rate_per_started_kg", 30, "RUL-007", unit="INR_per_started_kg", event="excess_luggage_registration_accepted", evidence_file=luggage_file, evidence="INR 30 per started kilogram", value_type="decimal"),
            _seed("luggage.registration_cutoff_minutes_before_origin", 60, "RUL-007", unit="minutes", event="excess_luggage_registration_accepted", evidence_file=luggage_file, evidence="no later than 60 minutes before origin departure"),
            _seed("luggage.excess_weight_rounding_increment_kg", 1, "RUL-007", unit="kg", event="excess_luggage_registration_accepted", evidence_file=luggage_file, evidence="rounded upward to one kilogram"),
            _seed("luggage.cancellation_fuller_refund_cutoff_hours", 4, "RUL-007", unit="hours", event="luggage_cancellation_accepted", evidence_file=luggage_file, evidence="more than four hours before departure"),
            _seed("luggage.cancellation_refund_percent", 80, "RUL-007", unit="percent", event="luggage_cancellation_accepted", evidence_file=luggage_file, evidence="refunds 80%", value_type="decimal"),
        ]
    )

    pet_file = f"{RULES}/RUL-008-pets.md"
    pet_values = [
        ("pet.maximum_per_booking", 1, "pets", "One registered pet is permitted per booking"),
        ("pet.registration_cutoff_hours_before_origin", 24, "hours", "at least 24 hours before origin departure"),
        ("pet.base_charge", 600, "INR", "INR 600 plus INR 20"),
        ("pet.charge_per_started_kg", 20, "INR_per_started_kg", "INR 600 plus INR 20 per started kilogram"),
        ("pet.fitness_certificate_max_age_days", 10, "days", "within ten days before travel"),
        ("pet.cancellation_refund_cutoff_hours", 24, "hours", "more than 24 hours before departure"),
        ("pet.cancellation_refund_percent", 80, "percent", "refunds 80%"),
        ("pet.assistance_animal_charge", 0, "INR", "without the pet charge"),
    ]
    for name, value, unit, evidence in pet_values:
        seeds.append(_seed(name, value, "RUL-008", unit=unit, event="pet_registration_or_cancellation_accepted", evidence_file=pet_file, evidence=evidence, value_type="decimal" if unit in {"INR", "INR_per_started_kg", "percent"} else "integer"))

    concession_file = f"{RULES}/RUL-009-concessions.md"
    concessions = {
        "student_mobility": (40, "| Student Mobility | 40%"),
        "senior_wellbeing": (25, "| Senior Wellbeing | 25%"),
        "accessible_travel": (50, "| Accessible Travel | 50%"),
        "service_family": (20, "| Service Family | 20%"),
    }
    for key, (percent, evidence) in concessions.items():
        seeds.append(_seed(f"concession.{key}.discount_percent", percent, "RUL-009", unit="percent", event="booking_created", evidence_file=concession_file, evidence=evidence, value_type="decimal"))
    seeds.append(_seed("concession.maximum_per_traveller", 1, "RUL-009", unit="concessions", event="booking_created", evidence_file=concession_file, evidence="One concession may be selected per traveller"))

    boarding_file = f"{RULES}/RUL-010-boarding-changes.md"
    seeds.extend(
        [
            _seed("boarding_change.maximum_changes", 1, "RUL-010", unit="changes", event="boarding_change_confirmed", evidence_file=boarding_file, evidence="one boarding-station change per booking"),
            _seed("boarding_change.cutoff_hours_before_origin", 6, "RUL-010", unit="hours", event="boarding_change_confirmed", evidence_file=boarding_file, evidence="more than six hours before scheduled departure"),
        ]
    )

    disruption_file = f"{RULES}/RUL-011-train-cancellations-delays.md"
    seeds.extend(
        [
            _seed("operator_cancellation.refund_start_hours", 24, "RUL-011", unit="hours", event="operator_cancellation_recorded", evidence_file=disruption_file, evidence="begin within 24 hours"),
            _seed("operator_cancellation.recorded_components_refund_percent", 100, "RUL-011", unit="percent", event="operator_cancellation_recorded", evidence_file=disruption_file, evidence="receives a full refund", value_type="decimal"),
            _seed("delay.full_refund_threshold_hours", 3, "RUL-011", unit="hours", event="delay_status_observed", evidence_file=disruption_file, evidence="at least three hours later"),
            _seed("delay.qualifying_unused_journey_refund_percent", 100, "RUL-011", unit="percent", event="delay_status_observed", evidence_file=disruption_file, evidence="claim the same full refund", value_type="decimal"),
            _seed("disruption.claim_deadline_hours_after_origin", 72, "RUL-011", unit="hours", event="disruption_claim_submitted", evidence_file=disruption_file, evidence="no later than 72 hours"),
        ]
    )

    complaint_file = f"{RULES}/RUL-012-complaints.md"
    complaint_values = [
        ("complaint.safety_ack_minutes", 15, "minutes", "target acknowledgement of 15 minutes"),
        ("complaint.privacy_security_ack_minutes", 60, "minutes", "Privacy or security cases target one hour"),
        ("complaint.active_travel_ack_minutes", 120, "minutes", "Active-travel booking issues target two hours"),
        ("complaint.refund_dispute_ack_business_days", 1, "business_days", "Refund and payment disputes target one business day"),
        ("complaint.other_service_ack_business_days", 2, "business_days", "Other service complaints target two business days"),
    ]
    for name, value, unit, evidence in complaint_values:
        seeds.append(_seed(name, value, "RUL-012", unit=unit, event="complaint_received", evidence_file=complaint_file, evidence=evidence))

    identity_file = f"{RULES}/RUL-006-identity-verification.md"
    seeds.append(_seed("identity.minor_age_exclusive", 16, "RUL-006", unit="years", event="identity_verified", evidence_file=identity_file, evidence="under 16"))

    seeds.append(
        _seed(
            "actions.pending_expiry_minutes",
            10,
            "SYSTEM-CONFIG",
            unit="minutes",
            event="action_proposed",
            evidence_file=None,
            evidence=(),
            effective_from=SYSTEM_BASELINE,
            precedence=1,
            note="Application-level default; no Ujjwal Rail rule specifies action expiry.",
        )
    )

    amendments = [
        ("cancel_fixed_charge_ac2", 260, "CIR-001", "2026-11-15T00:00:00+05:30", "cancellation_request_accepted", f"{CIRCULARS}/CIR-001.md", ("Previous value | INR 240", "Revised value | INR 260"), "INR"),
        ("cancel_fixed_charge_ac3", 220, "CIR-001", "2026-11-15T00:00:00+05:30", "cancellation_request_accepted", f"{CIRCULARS}/CIR-001.md", ("Previous value | INR 200", "Revised value | INR 220"), "INR"),
        ("tatkal_supplement_ac2", 450, "CIR-002", "2026-11-20T00:00:00+05:30", "tatkal_booking_completed", f"{CIRCULARS}/CIR-002.md", ("Previous value | INR 400", "Revised value | INR 450"), "INR"),
        ("tatkal_supplement_ac3", 330, "CIR-002", "2026-11-20T00:00:00+05:30", "tatkal_booking_completed", f"{CIRCULARS}/CIR-002.md", ("Previous value | INR 300", "Revised value | INR 330"), "INR"),
        ("excess_luggage_rate_per_started_kg", 35, "CIR-005", "2027-01-01T00:00:00+05:30", "excess_luggage_registration_accepted", f"{CIRCULARS}/CIR-005.md", ("Previous value | INR 30", "Revised value | INR 35"), "INR_per_started_kg"),
    ]
    for name, value, source_doc, effective_from, event, evidence_file, evidence, unit in amendments:
        seeds.append(_seed(name, value, source_doc, unit=unit, event=event, evidence_file=evidence_file, evidence=evidence, effective_from=effective_from, precedence=100, value_type="decimal", note="Explicit circular amendment."))

    return seeds


def verify_seed_sources(seeds: Iterable[SettingSeed]) -> list[str]:
    """Return reviewed-mapping problems without guessing replacement values."""

    problems: list[str] = []
    for seed in seeds:
        if seed.source_doc == "SYSTEM-CONFIG":
            if seed.evidence_file is not None:
                problems.append(f"{seed.name}: system setting unexpectedly cites a file")
            continue
        if not seed.evidence_file:
            problems.append(f"{seed.name}: missing evidence file")
            continue
        path = PROJECT_ROOT / seed.evidence_file
        if not path.exists():
            problems.append(f"{seed.name}: source file does not exist: {path}")
            continue
        content = path.read_text(encoding="utf-8")
        if f"doc_id: {seed.source_doc}" not in content:
            problems.append(f"{seed.name}: {path.name} does not declare {seed.source_doc}")
        for snippet in seed.evidence:
            if snippet not in content:
                problems.append(f"{seed.name}: reviewed evidence missing from {path.name}: {snippet!r}")
    return problems
