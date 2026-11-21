"""Deterministic consistency validation for generated railway operations."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from policy_settings.database import DEFAULT_DB_PATH

from .database import connect
from .generator import DATASET_ID, WEEKDAYS


MANDATORY_COLUMNS = {
    "stations": {"station_code", "name", "other_names", "city"},
    "trains": {"train_no", "name", "runs_on", "classes"},
    "train_stops": {"train_no", "station_code", "stop_order", "arrival", "departure", "day_offset"},
    "fares": {"train_no", "class", "from_code", "to_code", "fare"},
    "seats": {"train_no", "journey_date", "class", "available", "rac", "waitlist"},
    "passengers": {"passenger_id", "name", "phone_last4", "preferred_language", "home_city"},
    "bookings": {"booking_id", "passenger_id", "train_no", "journey_date", "from_code", "to_code", "class", "amount_paid", "status", "booked_at"},
    "booking_travellers": {"booking_id", "traveller_name", "age", "status", "coach", "berth"},
    "actions": {"action_id", "passenger_id", "booking_id", "action_type", "status", "created_at", "expires_at", "result"},
    "settings": {"name", "value", "source_doc"},
}


def _load(data_dir: Path, name: str) -> Any:
    return json.loads((data_dir / name).read_text(encoding="utf-8"))


def _absolute_minutes(stop: dict[str, Any], event: str) -> int | None:
    value = stop[event]
    if value is None:
        return None
    hour, minute = map(int, value.split(":"))
    return stop["day_offset"] * 1440 + hour * 60 + minute


def validate_dataset(data_dir: Path, *, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    stations = _load(data_dir, "stations.json")
    trains = _load(data_dir, "trains.json")
    stops = _load(data_dir, "train_stops.json")
    fares = _load(data_dir, "fares.json")
    capacities = _load(data_dir, "train_capacities.json")
    seats = _load(data_dir, "seats.json")
    passengers = _load(data_dir, "passengers.json")
    bookings = _load(data_dir, "bookings.json")
    travellers = _load(data_dir, "booking_travellers.json")
    cancellations = _load(data_dir, "service_cancellations.json")
    edge = _load(data_dir, "edge_cases.json")
    manifest = _load(data_dir, "generation_manifest.json")

    station_codes = {x["station_code"] for x in stations}
    train_map = {x["train_no"]: x for x in trains}
    passenger_ids = {x["passenger_id"] for x in passengers}
    capacity_map = {(x["train_no"], x["class"]): x for x in capacities}
    stops_by_train: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in stops:
        stops_by_train[row["train_no"]].append(row)
    for route in stops_by_train.values():
        route.sort(key=lambda x: x["stop_order"])
    travellers_by_booking: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in travellers:
        travellers_by_booking[row["booking_id"]].append(row)
    cancellations_set = {(x["train_no"], x["journey_date"]) for x in cancellations}
    reference = date.fromisoformat(manifest["reference_date"])

    results: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        results.append({"check": name, "status": "PASS" if condition else "FAIL", "detail": detail})

    check("station_count", len(stations) >= 15, str(len(stations)))
    check("train_count", len(trains) >= 25, str(len(trains)))
    check("unique_primary_ids", len(station_codes) == len(stations) and len(train_map) == len(trains) and len(passenger_ids) == len(passengers))
    check("two_valid_stops_per_train", all(len(stops_by_train[t]) >= 2 and len({x['station_code'] for x in stops_by_train[t]}) == len(stops_by_train[t]) for t in train_map))
    check("stop_order", all([x["stop_order"] for x in route] == list(range(1, len(route) + 1)) for route in stops_by_train.values()))
    timeline_ok = True
    overnight = False
    for route in stops_by_train.values():
        prior = -1
        for stop in route:
            arrival = _absolute_minutes(stop, "arrival")
            departure = _absolute_minutes(stop, "departure")
            if arrival is not None and arrival <= prior:
                timeline_ok = False
            if arrival is not None:
                prior = arrival
            if departure is not None and departure < prior:
                timeline_ok = False
            if departure is not None:
                prior = departure
            overnight = overnight or stop["day_offset"] > 0
    check("chronological_stop_timeline", timeline_ok)
    check("overnight_train", overnight)
    check("valid_running_days", all(set(x["runs_on"]).issubset(WEEKDAYS) and x["runs_on"] for x in trains))

    fare_ok = True
    for fare in fares:
        route_codes = [x["station_code"] for x in stops_by_train.get(fare["train_no"], [])]
        fare_ok &= fare["train_no"] in train_map and fare["class"] in train_map[fare["train_no"]]["classes"]
        fare_ok &= fare["from_code"] in route_codes and fare["to_code"] in route_codes
        fare_ok &= route_codes.index(fare["from_code"]) < route_codes.index(fare["to_code"]) and isinstance(fare["fare"], int) and fare["fare"] > 0
    check("fares_valid", fare_ok, str(len(fares)))

    seat_keys = {(x["train_no"], x["journey_date"], x["class"]) for x in seats}
    seat_valid = True
    expected_seat_keys = set()
    for train in trains:
        for offset in range(14):
            service_date = reference + timedelta(days=offset)
            if WEEKDAYS[service_date.weekday()] in train["runs_on"]:
                for class_code in train["classes"]:
                    expected_seat_keys.add((train["train_no"], service_date.isoformat(), class_code))
    for seat in seats:
        key = (seat["train_no"], seat["journey_date"], seat["class"])
        service_date = date.fromisoformat(seat["journey_date"])
        seat_valid &= seat["train_no"] in train_map and seat["class"] in train_map[seat["train_no"]]["classes"]
        seat_valid &= reference <= service_date <= reference + timedelta(days=13)
        seat_valid &= WEEKDAYS[service_date.weekday()] in train_map[seat["train_no"]]["runs_on"]
        seat_valid &= key in seat_keys
    check("seat_rows_valid", seat_valid and len(seat_keys) == len(seats))
    check("seat_horizon_complete", seat_keys == expected_seat_keys, f"expected={len(expected_seat_keys)} actual={len(seat_keys)}")
    check("passenger_count", len(passengers) >= 25, str(len(passengers)))
    check("booking_count", len(bookings) >= 50, str(len(bookings)))
    required_statuses = {"CONFIRMED", "RAC", "WAITLISTED", "CANCELLED", "OPERATOR_CANCELLED"}
    check("required_booking_statuses", required_statuses.issubset({x["status"] for x in bookings}), str(sorted({x['status'] for x in bookings})))

    booking_refs_ok = True
    booking_operating_date_ok = True
    amount_ok = True
    aggregate_ok = True
    traveller_ok = True
    active_allocations: Counter[tuple[str, str, str, str]] = Counter()
    for booking in bookings:
        route_codes = [x["station_code"] for x in stops_by_train.get(booking["train_no"], [])]
        service_date = date.fromisoformat(booking["journey_date"])
        booking_refs_ok &= booking["passenger_id"] in passenger_ids and booking["train_no"] in train_map
        booking_refs_ok &= booking["from_code"] in route_codes and booking["to_code"] in route_codes
        booking_refs_ok &= route_codes.index(booking["from_code"]) < route_codes.index(booking["to_code"])
        booking_refs_ok &= booking["class"] in train_map[booking["train_no"]]["classes"]
        booking_operating_date_ok &= WEEKDAYS[service_date.weekday()] in train_map[booking["train_no"]]["runs_on"]
        people = travellers_by_booking[booking["booking_id"]]
        traveller_ok &= bool(people) and all(x["status"] in {"CNF", "RAC", "WL"} for x in people)
        matching_fare = next((x["fare"] for x in fares if x["train_no"] == booking["train_no"] and x["class"] == booking["class"] and x["from_code"] == booking["from_code"] and x["to_code"] == booking["to_code"]), None)
        amount_ok &= matching_fare is not None and booking["amount_paid"] == matching_fare * len(people)
        if booking["status"] not in {"CANCELLED", "OPERATOR_CANCELLED"}:
            status_set = {x["status"] for x in people}
            expected = "CONFIRMED" if status_set == {"CNF"} else "RAC" if status_set == {"RAC"} else "WAITLISTED" if status_set == {"WL"} else "MIXED"
            aggregate_ok &= booking["status"] == expected
        if booking["status"] not in {"CANCELLED", "OPERATOR_CANCELLED"}:
            for person in people:
                active_allocations[(booking["train_no"], booking["journey_date"], booking["class"], person["status"])] += 1
    check("booking_references_and_routes", booking_refs_ok)
    check("bookings_on_operating_dates", booking_operating_date_ok)
    check("booking_amounts_match_fares", amount_ok)
    check("booking_aggregate_statuses", aggregate_ok)
    check("travellers_valid", traveller_ok and set(travellers_by_booking) == {x["booking_id"] for x in bookings})

    inventory_ok = True
    capacity_ok = True
    state_examples = {"available": False, "rac": False, "waitlist": False, "unavailable": False}
    for seat in seats:
        key3 = (seat["train_no"], seat["journey_date"], seat["class"])
        cnf = active_allocations[key3 + ("CNF",)]
        rac = active_allocations[key3 + ("RAC",)]
        wl = active_allocations[key3 + ("WL",)]
        cancelled = (seat["train_no"], seat["journey_date"]) in cancellations_set
        if cancelled:
            inventory_ok &= seat["service_status"] == "CANCELLED" and seat["available"] == seat["rac"] == seat["waitlist"] == 0
        else:
            inventory_ok &= seat["available"] == seat["confirmed_capacity"] - cnf
            inventory_ok &= seat["rac"] == seat["rac_capacity"] - rac and seat["waitlist"] == seat["waitlist_capacity"] - wl
        capacity_ok &= cnf <= seat["confirmed_capacity"] and rac <= seat["rac_capacity"] and wl <= seat["waitlist_capacity"]
        state_examples["available"] |= seat["available"] > 0
        state_examples["rac"] |= seat["available"] == 0 and seat["rac"] > 0
        state_examples["waitlist"] |= seat["available"] == 0 and seat["rac"] == 0 and seat["waitlist"] > 0
        state_examples["unavailable"] |= seat["available"] == seat["rac"] == seat["waitlist"] == 0
    check("capacity_limits", capacity_ok)
    check("remaining_inventory_reconciled", inventory_ok)
    cancelled_ids = {x["booking_id"] for x in bookings if x["status"] == "CANCELLED"}
    check("passenger_cancellations_do_not_consume_inventory", bool(cancelled_ids) and all(x["booking_id"] in travellers_by_booking for x in bookings if x["booking_id"] in cancelled_ids))
    check("all_inventory_states", all(state_examples.values()), str(state_examples))

    op_cancel_ok = all((x["train_no"], x["journey_date"]) in cancellations_set for x in bookings if x["status"] == "OPERATOR_CANCELLED")
    op_cancel_ok &= all(not ((x["train_no"], x["journey_date"]) in cancellations_set) for x in bookings if x["status"] not in {"OPERATOR_CANCELLED"})
    check("operator_cancellations_consistent", op_cancel_ok)
    booked_passengers = {x["passenger_id"] for x in bookings}
    check("passenger_without_bookings", bool(passenger_ids - booked_passengers), str(sorted(passenger_ids - booked_passengers)))
    mixed = [x for x in bookings if {y["status"] for y in travellers_by_booking[x["booking_id"]]} >= {"CNF", "WL"}]
    check("mixed_cnf_wl_booking", bool(mixed), mixed[0]["booking_id"] if mixed else "")
    case_ids = {x["case_id"] for x in edge["cases"]}
    check("cutoff_boundary_cases", {"EDGE-CUTOFF-EXACT", "EDGE-CUTOFF-AFTER-ONE-MINUTE"}.issubset(case_ids))
    aliases = defaultdict(set)
    for station in stations:
        for alias in station["other_names"]:
            aliases[alias.casefold()].add(station["station_code"])
    check("ambiguous_station_alias", any(len(codes) >= 2 for codes in aliases.values()))

    with connect(db_path) as connection:
        schema_ok = True
        for table, required in MANDATORY_COLUMNS.items():
            columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            schema_ok &= required.issubset(columns)
        check("mandatory_sqlite_schema", schema_ok)
        settings_count = connection.execute("SELECT COUNT(*) FROM settings").fetchone()[0]
        versions_count = connection.execute("SELECT COUNT(*) FROM setting_versions").fetchone()[0]
        known_setting = connection.execute("SELECT value, source_doc FROM settings WHERE name = 'actions.pending_expiry_minutes'").fetchone()
        check("settings_preserved", settings_count >= 88 and versions_count >= 93 and tuple(known_setting or ()) == ("10", "SYSTEM-CONFIG"), f"settings={settings_count}, versions={versions_count}")
        fk_rows = connection.execute("PRAGMA foreign_key_check").fetchall()
        check("foreign_key_integrity", not fk_rows, str([tuple(x) for x in fk_rows]))
        db_counts_ok = all(
            connection.execute(f"SELECT COUNT(*) FROM {table} WHERE dataset_id = ?", (DATASET_ID,)).fetchone()[0] == expected
            for table, expected in [
                ("stations", len(stations)), ("trains", len(trains)), ("train_stops", len(stops)),
                ("fares", len(fares)), ("seats", len(seats)), ("passengers", len(passengers)),
                ("bookings", len(bookings)), ("booking_travellers", len(travellers)),
            ]
        )
        check("json_sqlite_counts_match", db_counts_ok)

    passed = sum(x["status"] == "PASS" for x in results)
    return {
        "dataset_id": DATASET_ID,
        "validated_at": datetime.now().astimezone().isoformat(),
        "summary": {"passed": passed, "failed": len(results) - passed, "total": len(results)},
        "checks": results,
    }
