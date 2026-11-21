"""Deterministic generation of reviewable Ujjwal Rail operational JSON."""

from __future__ import annotations

import json
import random
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from policy_settings.database import DEFAULT_DB_PATH, PROJECT_ROOT
from policy_settings.repository import get_setting_int


IST = timezone(timedelta(hours=5, minutes=30))
DATASET_ID = "ujjwal-demo-v1"
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
SUPPORTED_CLASSES = ("FP", "AC2", "AC3", "EC", "SL", "CC")


CREATIVE_CATALOG = {
    "stations": [
        ("ANPR", "Anandpur Central", ["Anandpur", "Anand Pur", "Anandpur Kendra"], "Anandpur"),
        ("ANPN", "Anandpur North", ["Anandpur", "Anand Pur Uttar", "Anandpur North"], "Anandpur"),
        ("MTRP", "Mitrapur Junction", ["Mitrapur", "Mitra Pur Jn"], "Mitrapur"),
        ("SURY", "Suryanagar", ["Surya Nagar", "Suryanagar Station"], "Suryanagar"),
        ("NIRM", "Nirmalganj", ["Nirmal Ganj", "Nirmalganj Road"], "Nirmalganj"),
        ("KAVA", "Kaveripuram", ["Kaveri Puram", "Kaveripur"], "Kaveripuram"),
        ("VIND", "Vindhyapur", ["Vindhya Pur", "Vindhyapur City"], "Vindhyapur"),
        ("CHET", "Chetakgarh", ["Chetak Garh", "Chetak Fort"], "Chetakgarh"),
        ("NEEL", "Neelkanth City", ["Neel Kanth", "Neelkanth"], "Neelkanth"),
        ("UDAY", "Udayabad", ["Udaya Bad", "Udayabad Town"], "Udayabad"),
        ("SAHY", "Sahyadri Road", ["Sahyadri", "Sahyadri Rd"], "Sahyadri"),
        ("KOSA", "Koshalpur", ["Kaushal Pur", "Koshalpur City"], "Koshalpur"),
        ("RATN", "Ratnadeep", ["Ratna Deep", "Ratnadeep Nagar"], "Ratnadeep"),
        ("MALV", "Malvanagar", ["Malva Nagar", "Malvanagar East"], "Malvanagar"),
        ("TUNG", "Tungabhadra Town", ["Tunga Bhadra", "Tungabhadra"], "Tungabhadra"),
        ("ARUN", "Arunoday", ["Arun Uday", "Arunoday City"], "Arunoday"),
        ("PAVA", "Pavanpur", ["Pawan Pur", "Pavanpur Road"], "Pavanpur"),
        ("MEGH", "Meghvan", ["Megh Van", "Meghvan Central"], "Meghvan"),
    ],
    "train_names": [
        "Raat Kamal Express", "Ujjwal Setu", "Mitra Shakti", "Surya Rekha", "Neel Dhara",
        "Vindhya Vihar", "Kaveri Jyoti", "Chetak Sandhya", "Arunoday Link", "Sahyadri Saathi",
        "Ratnadeep Mail", "Pavan Path", "Koshal Connect", "Megh Tarang", "Nirmal Tejas",
        "Tunga Pravah", "Malva Manzil", "Anand Udaan", "Uday Pragati", "Neelkanth Rapid",
        "Mitra Nagar Intercity", "Surya Sakha", "Vindhya Nightline", "Kaveri Commuter", "Ujjwal Parikrama",
    ],
    "passengers": [
        ("Aarav Nayan", "Anandpur", "1842", "English"),
        ("Meera Tapan", "Mitrapur", "2607", "Hindi"),
        ("Kabir Veda", "Suryanagar", "7315", "Hinglish"),
        ("Naina Ilesh", "Kaveripuram", "4086", "English"),
        ("Rohan Devik", "Vindhyapur", "9521", "Hindi"),
        ("Ira Suman", "Chetakgarh", "3174", "Hinglish"),
        ("Vivaan Ritam", "Neelkanth", "6408", "English"),
        ("Tara Mihir", "Udayabad", "8253", "Hindi"),
        ("Arjun Lekh", "Sahyadri", "1936", "Hinglish"),
        ("Diya Varen", "Koshalpur", "5742", "English"),
        ("Neil Amod", "Ratnadeep", "2861", "Hindi"),
        ("Kavya Rishit", "Malvanagar", "9037", "Hinglish"),
        ("Advay Nihar", "Tungabhadra", "4529", "English"),
        ("Sana Ojas", "Arunoday", "6180", "Hindi"),
        ("Reyansh Tanuj", "Pavanpur", "3475", "Hinglish"),
        ("Myra Eshan", "Meghvan", "7604", "English"),
        ("Yuvan Prerit", "Anandpur", "1298", "Hindi"),
        ("Aisha Navit", "Mitrapur", "8351", "Hinglish"),
        ("Dhruv Kiran", "Suryanagar", "4960", "English"),
        ("Riya Anek", "Nirmalganj", "2713", "Hindi"),
        ("Vihaan Urjit", "Kaveripuram", "6847", "Hinglish"),
        ("Anaya Ronav", "Vindhyapur", "3502", "English"),
        ("Krish Tvesh", "Chetakgarh", "9176", "Hindi"),
        ("Siya Mudit", "Neelkanth", "5284", "Hinglish"),
        ("Ahaan Viraj", "Udayabad", "1439", "English"),
    ],
}


def _json_dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _minutes_to_hhmm(minutes: int) -> str:
    minute_of_day = minutes % (24 * 60)
    return f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}"


def _parse_hhmm(value: str) -> tuple[int, int]:
    hour, minute = value.split(":")
    return int(hour), int(minute)


def _service_datetime(journey_date: date, stop: dict[str, Any]) -> datetime:
    value = stop["departure"] or stop["arrival"]
    hour, minute = _parse_hhmm(value)
    return datetime.combine(
        journey_date + timedelta(days=stop["day_offset"]),
        time(hour, minute),
        tzinfo=IST,
    )


def _runs_on(train: dict[str, Any], journey_date: date) -> bool:
    return WEEKDAYS[journey_date.weekday()] in train["runs_on"]


def _first_running_date(train: dict[str, Any], start: date, horizon: int = 14) -> date:
    for offset in range(horizon):
        candidate = start + timedelta(days=offset)
        if _runs_on(train, candidate):
            return candidate
    raise ValueError(f"{train['train_no']} has no service within horizon")


def _make_trains_and_stops(
    stations: list[dict[str, Any]], train_names: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    class_patterns = [
        ["FP", "AC2", "AC3", "SL"],
        ["AC2", "AC3", "SL"],
        ["FP", "AC2", "EC", "CC"],
        ["AC3", "SL", "CC"],
        ["AC2", "AC3", "EC"],
    ]
    run_patterns = [
        list(WEEKDAYS),
        ["Mon", "Wed", "Fri", "Sun"],
        ["Tue", "Thu", "Sat"],
        ["Mon", "Tue", "Thu", "Sat"],
        ["Wed", "Fri", "Sun"],
    ]
    trains: list[dict[str, Any]] = []
    stops: list[dict[str, Any]] = []
    station_codes = [station["station_code"] for station in stations]

    for index in range(25):
        train_no = f"UJ{1001 + index}"
        route_length = 4 + (index % 3)
        step = 1 + (index % 4)
        start_index = (index * 3) % len(station_codes)
        route = [station_codes[(start_index + step * item) % len(station_codes)] for item in range(route_length)]
        if len(set(route)) != route_length:
            raise ValueError(f"generated duplicate route station for {train_no}")
        start_minutes = 23 * 60 + 40 if index == 0 else 5 * 60 + 20 + ((index * 47) % 900)
        segment_minutes = 75 + (index % 4) * 20
        classes = class_patterns[index % len(class_patterns)]
        runs = list(WEEKDAYS) if index < 10 else run_patterns[index % len(run_patterns)]
        trains.append(
            {
                "dataset_id": DATASET_ID,
                "train_no": train_no,
                "name": train_names[index],
                "runs_on": runs,
                "classes": classes,
            }
        )
        absolute_departure = start_minutes
        for order, station_code in enumerate(route, start=1):
            if order == 1:
                arrival = None
                departure = _minutes_to_hhmm(absolute_departure)
                absolute_event = absolute_departure
            else:
                absolute_arrival = absolute_departure + segment_minutes
                arrival = _minutes_to_hhmm(absolute_arrival)
                absolute_event = absolute_arrival
                if order == len(route):
                    departure = None
                else:
                    absolute_departure = absolute_arrival + 10
                    departure = _minutes_to_hhmm(absolute_departure)
            stops.append(
                {
                    "dataset_id": DATASET_ID,
                    "train_no": train_no,
                    "station_code": station_code,
                    "stop_order": order,
                    "arrival": arrival,
                    "departure": departure,
                    "day_offset": absolute_event // (24 * 60),
                }
            )
    return trains, stops


def _capacity(train_no: str, class_code: str) -> tuple[int, int, int]:
    if train_no == "UJ1001" and class_code == "FP":
        return 1, 0, 3
    if train_no == "UJ1002" and class_code == "AC2":
        return 1, 2, 2
    if train_no == "UJ1003" and class_code == "FP":
        return 1, 0, 1
    confirmed = {"FP": 12, "AC2": 24, "AC3": 36, "EC": 40, "SL": 48, "CC": 50}[class_code]
    rac = 0 if class_code == "FP" else max(4, confirmed // 8)
    waitlist = max(8, confirmed // 5)
    return confirmed, rac, waitlist


def _aggregate_status(statuses: list[str]) -> str:
    unique = set(statuses)
    if unique == {"CNF"}:
        return "CONFIRMED"
    if unique == {"RAC"}:
        return "RAC"
    if unique == {"WL"}:
        return "WAITLISTED"
    return "MIXED"


def generate_dataset(
    output_dir: Path,
    *,
    reference_date: date = date(2026, 11, 21),
    seed: int = 42,
    db_path: Path = DEFAULT_DB_PATH,
    creative_catalog: dict[str, Any] | None = None,
    creative_generation: str = "deterministic-curated-fallback (no external LLM invoked)",
) -> dict[str, Any]:
    """Generate JSON records and return a manifest of files and counts."""

    random.Random(seed)  # Establish and record deterministic generation contract.
    output_dir.mkdir(parents=True, exist_ok=True)

    catalog = creative_catalog or CREATIVE_CATALOG
    if len(catalog["stations"]) < 15 or len(catalog["train_names"]) < 25 or len(catalog["passengers"]) < 25:
        raise ValueError("creative catalog must contain at least 15 stations, 25 train names and 25 passengers")
    stations = [
        {
            "dataset_id": DATASET_ID,
            "station_code": code,
            "name": name,
            "other_names": aliases,
            "city": city,
        }
        for code, name, aliases, city in catalog["stations"]
    ]
    trains, train_stops = _make_trains_and_stops(stations, catalog["train_names"])
    train_by_no = {train["train_no"]: train for train in trains}
    stops_by_train: dict[str, list[dict[str, Any]]] = {}
    for stop in train_stops:
        stops_by_train.setdefault(stop["train_no"], []).append(stop)

    fare_per_segment_paise = {"FP": 85000, "AC2": 60000, "AC3": 45000, "EC": 50000, "SL": 25000, "CC": 30000}
    fares: list[dict[str, Any]] = []
    fare_lookup: dict[tuple[str, str, str, str], int] = {}
    capacities: list[dict[str, Any]] = []
    for train_index, train in enumerate(trains):
        route = stops_by_train[train["train_no"]]
        for class_code in train["classes"]:
            confirmed, rac, waitlist = _capacity(train["train_no"], class_code)
            capacities.append(
                {
                    "dataset_id": DATASET_ID,
                    "train_no": train["train_no"],
                    "class": class_code,
                    "confirmed_capacity": confirmed,
                    "rac_capacity": rac,
                    "waitlist_capacity": waitlist,
                }
            )
            for origin_index in range(len(route) - 1):
                for destination_index in range(origin_index + 1, len(route)):
                    segments = destination_index - origin_index
                    fare = (fare_per_segment_paise[class_code] + train_index * 250) * segments
                    key = (train["train_no"], class_code, route[origin_index]["station_code"], route[destination_index]["station_code"])
                    fare_lookup[key] = fare
                    fares.append(
                        {
                            "dataset_id": DATASET_ID,
                            "train_no": train["train_no"],
                            "class": class_code,
                            "from_code": key[2],
                            "to_code": key[3],
                            "fare": fare,
                        }
                    )

    cancellation_date = reference_date + timedelta(days=5)
    service_cancellations = [
        {
            "dataset_id": DATASET_ID,
            "train_no": "UJ1005",
            "journey_date": cancellation_date.isoformat(),
            "reason": "Fictional route-control closure for operator-cancellation testing",
            "announced_at": datetime.combine(reference_date + timedelta(days=2), time(10, 0), tzinfo=IST).isoformat(),
        }
    ]
    cancelled_services = {(item["train_no"], item["journey_date"]) for item in service_cancellations}

    capacity_lookup = {(item["train_no"], item["class"]): item for item in capacities}
    seats: list[dict[str, Any]] = []
    seat_lookup: dict[tuple[str, str, str], dict[str, Any]] = {}
    for train in trains:
        for offset in range(14):
            service_date = reference_date + timedelta(days=offset)
            if not _runs_on(train, service_date):
                continue
            for class_code in train["classes"]:
                capacity = capacity_lookup[(train["train_no"], class_code)]
                cancelled = (train["train_no"], service_date.isoformat()) in cancelled_services
                row = {
                    "dataset_id": DATASET_ID,
                    "train_no": train["train_no"],
                    "journey_date": service_date.isoformat(),
                    "class": class_code,
                    "available": 0 if cancelled else capacity["confirmed_capacity"],
                    "rac": 0 if cancelled else capacity["rac_capacity"],
                    "waitlist": 0 if cancelled else capacity["waitlist_capacity"],
                    "confirmed_capacity": capacity["confirmed_capacity"],
                    "rac_capacity": capacity["rac_capacity"],
                    "waitlist_capacity": capacity["waitlist_capacity"],
                    "service_status": "CANCELLED" if cancelled else "SCHEDULED",
                }
                seats.append(row)
                seat_lookup[(train["train_no"], service_date.isoformat(), class_code)] = row

    passengers = [
        {
            "dataset_id": DATASET_ID,
            "passenger_id": f"P{index:03d}",
            "name": name,
            "phone_last4": phone_last4,
            "preferred_language": language,
            "home_city": city,
        }
        for index, (name, city, phone_last4, language) in enumerate(catalog["passengers"][:25], start=1)
    ]
    passenger_by_id = {item["passenger_id"]: item for item in passengers}

    bookings: list[dict[str, Any]] = []
    travellers: list[dict[str, Any]] = []
    traveller_counter = 1
    companion_names = ["Aadi Nayan", "Mira Tapan", "Kian Veda", "Rhea Ilesh", "Dev Ritam", "Tia Suman"]

    def add_booking(
        booking_id: str,
        passenger_id: str,
        train_no: str,
        journey_date: date,
        class_code: str,
        traveller_count: int,
        *,
        status_override: str | None = None,
        historical_statuses: list[str] | None = None,
        from_index: int = 0,
        to_index: int | None = None,
    ) -> None:
        nonlocal traveller_counter
        train = train_by_no[train_no]
        route = stops_by_train[train_no]
        destination_index = len(route) - 1 if to_index is None else to_index
        from_code = route[from_index]["station_code"]
        to_code = route[destination_index]["station_code"]
        if not _runs_on(train, journey_date):
            raise ValueError(f"booking {booking_id} uses non-running service")
        if class_code not in train["classes"]:
            raise ValueError(f"booking {booking_id} uses unsupported class")
        if (train_no, journey_date.isoformat()) in cancelled_services and status_override != "OPERATOR_CANCELLED":
            raise ValueError(f"active booking attempted on cancelled service: {booking_id}")

        statuses: list[str] = []
        consume = status_override not in {"CANCELLED", "OPERATOR_CANCELLED"}
        seat = seat_lookup[(train_no, journey_date.isoformat(), class_code)]
        for traveller_index in range(traveller_count):
            if historical_statuses:
                traveller_status = historical_statuses[traveller_index]
            elif consume:
                if seat["available"] > 0:
                    traveller_status = "CNF"
                    seat["available"] -= 1
                elif seat["rac"] > 0:
                    traveller_status = "RAC"
                    seat["rac"] -= 1
                elif seat["waitlist"] > 0:
                    traveller_status = "WL"
                    seat["waitlist"] -= 1
                else:
                    raise ValueError(f"no inventory for booking {booking_id}")
            else:
                traveller_status = "CNF"
            statuses.append(traveller_status)
            coach = None
            berth = None
            if traveller_status == "CNF":
                coach = f"{class_code}-C{1 + (traveller_counter % 4)}"
                berth = f"{1 + (traveller_counter % 72):02d}"
            elif traveller_status == "RAC":
                coach = f"{class_code}-RAC"
                berth = f"RAC-{1 + (traveller_counter % 20):02d}"
            primary_name = passenger_by_id[passenger_id]["name"]
            traveller_name = primary_name if traveller_index == 0 else companion_names[(traveller_counter + traveller_index) % len(companion_names)]
            travellers.append(
                {
                    "dataset_id": DATASET_ID,
                    "traveller_id": f"TRV{traveller_counter:04d}",
                    "booking_id": booking_id,
                    "traveller_name": traveller_name,
                    "age": 18 + ((traveller_counter * 7) % 55),
                    "status": traveller_status,
                    "coach": coach,
                    "berth": berth,
                }
            )
            traveller_counter += 1

        status = status_override or _aggregate_status(statuses)
        booked_at = datetime.combine(reference_date - timedelta(days=10 + int(booking_id[-2:]) % 20), time(9, 15), tzinfo=IST)
        boarding_datetime = _service_datetime(journey_date, route[from_index])
        amount_paid = fare_lookup[(train_no, class_code, from_code, to_code)] * traveller_count
        cancelled_at = None
        cancellation_type = None
        if status == "CANCELLED":
            cancelled_at = (boarding_datetime - timedelta(hours=72)).isoformat()
            cancellation_type = "PASSENGER"
        elif status == "OPERATOR_CANCELLED":
            cancelled_at = service_cancellations[0]["announced_at"]
            cancellation_type = "OPERATOR"
        bookings.append(
            {
                "dataset_id": DATASET_ID,
                "booking_id": booking_id,
                "passenger_id": passenger_id,
                "train_no": train_no,
                "journey_date": journey_date.isoformat(),
                "from_code": from_code,
                "to_code": to_code,
                "class": class_code,
                "amount_paid": amount_paid,
                "status": status,
                "booked_at": booked_at.isoformat(),
                "boarding_datetime": boarding_datetime.isoformat(),
                "cancelled_at": cancelled_at,
                "cancellation_type": cancellation_type,
            }
        )

    # Deliberate inventory and workflow scenarios.
    add_booking("BKG0001", "P001", "UJ1006", _first_running_date(train_by_no["UJ1006"], reference_date + timedelta(days=4)), "AC2", 1)
    add_booking("BKG0002", "P002", "UJ1007", _first_running_date(train_by_no["UJ1007"], reference_date + timedelta(days=5)), "AC3", 1)
    add_booking("BKG0003", "P003", "UJ1001", reference_date, "FP", 2)  # CNF + WL
    add_booking("BKG0004", "P004", "UJ1002", reference_date, "AC2", 1)  # fills CNF
    add_booking("BKG0005", "P005", "UJ1002", reference_date, "AC2", 1)  # RAC
    add_booking("BKG0006", "P006", "UJ1003", reference_date, "FP", 1)  # fills CNF
    add_booking("BKG0007", "P007", "UJ1003", reference_date, "FP", 1)  # fills WL
    add_booking("BKG0008", "P008", "UJ1005", cancellation_date, "AC2", 1, status_override="OPERATOR_CANCELLED", historical_statuses=["CNF"])
    add_booking("BKG0009", "P009", "UJ1005", cancellation_date, "AC3", 1, status_override="OPERATOR_CANCELLED", historical_statuses=["RAC"])
    add_booking("BKG0010", "P010", "UJ1008", _first_running_date(train_by_no["UJ1008"], reference_date + timedelta(days=2)), "AC2", 1, status_override="CANCELLED", historical_statuses=["CNF"])

    for number in range(11, 51):
        booking_id = f"BKG{number:04d}"
        passenger_id = f"P{1 + ((number - 1) % 24):03d}"  # P025 deliberately has no bookings.
        if number == 16:
            add_booking(booking_id, passenger_id, "UJ1005", cancellation_date, "EC", 1, status_override="OPERATOR_CANCELLED", historical_statuses=["CNF"])
            continue
        train_no = f"UJ{1006 + ((number - 11) % 20)}"
        train = train_by_no[train_no]
        start = reference_date + timedelta(days=number % 12)
        journey_date = _first_running_date(train, start, 14 - (start - reference_date).days)
        class_code = train["classes"][number % len(train["classes"])]
        traveller_count = 1 + (number % 3)
        status_override = "CANCELLED" if 11 <= number <= 15 else None
        add_booking(
            booking_id,
            passenger_id,
            train_no,
            journey_date,
            class_code,
            traveller_count,
            status_override=status_override,
            historical_statuses=["CNF"] * traveller_count if status_override else None,
            from_index=1 if number % 5 == 0 else 0,
        )

    boundary_hours, boundary_source = get_setting_int(
        "cancellation.band_a.lower_hours_exclusive",
        reference_date.isoformat(),
        db_path=db_path,
    )
    booking_lookup = {item["booking_id"]: item for item in bookings}
    exact_departure = datetime.fromisoformat(booking_lookup["BKG0001"]["boarding_datetime"])
    after_departure = datetime.fromisoformat(booking_lookup["BKG0002"]["boarding_datetime"])
    edge_cases = {
        "dataset_id": DATASET_ID,
        "reference_date": reference_date.isoformat(),
        "status_mappings": {
            "CONFIRMED": "All active travellers are CNF",
            "RAC": "All active travellers are RAC",
            "WAITLISTED": "All active travellers are WL",
            "MIXED": "Active travellers have more than one CNF/RAC/WL status",
            "CANCELLED": "Passenger-initiated cancellation; traveller status preserves historical allocation",
            "OPERATOR_CANCELLED": "Service cancelled by Ujjwal Rail; traveller status preserves historical allocation",
        },
        "inventory_semantics": "available, rac and waitlist are remaining train-and-class-level capacity after active synthetic allocations; no segment reuse is modelled",
        "cases": [
            {
                "case_id": "EDGE-CUTOFF-EXACT",
                "booking_id": "BKG0001",
                "requested_cancellation_at": (exact_departure - timedelta(hours=boundary_hours)).isoformat(),
                "remaining_time": f"exactly {boundary_hours} hours",
                "expected_bracket": "B",
                "policy_source": boundary_source,
            },
            {
                "case_id": "EDGE-CUTOFF-AFTER-ONE-MINUTE",
                "booking_id": "BKG0002",
                "requested_cancellation_at": (after_departure - timedelta(hours=boundary_hours) + timedelta(minutes=1)).isoformat(),
                "remaining_time": f"{boundary_hours - 1} hours 59 minutes",
                "expected_bracket": "B",
                "policy_source": boundary_source,
            },
            {"case_id": "EDGE-OVERNIGHT", "train_no": "UJ1001", "description": "Departs 23:40 and has downstream stops with day_offset 1."},
            {"case_id": "EDGE-MIXED-STATUS", "booking_id": "BKG0003", "traveller_statuses": ["CNF", "WL"]},
            {"case_id": "EDGE-NO-BOOKINGS", "passenger_id": "P025"},
            {"case_id": "EDGE-SIMILAR-STATIONS", "station_codes": ["ANPR", "ANPN"], "ambiguous_query": "Anandpur se train dikhao"},
            {"case_id": "EDGE-INVENTORY-RAC", "train_no": "UJ1002", "journey_date": reference_date.isoformat(), "class": "AC2"},
            {"case_id": "EDGE-INVENTORY-WAITLIST", "train_no": "UJ1001", "journey_date": reference_date.isoformat(), "class": "FP"},
            {"case_id": "EDGE-INVENTORY-UNAVAILABLE", "train_no": "UJ1003", "journey_date": reference_date.isoformat(), "class": "FP"},
            {"case_id": "EDGE-OPERATOR-CANCELLED", "train_no": "UJ1005", "journey_date": cancellation_date.isoformat(), "booking_ids": ["BKG0008", "BKG0009", "BKG0016"]},
        ],
    }

    files = {
        "stations.json": stations,
        "trains.json": trains,
        "train_stops.json": train_stops,
        "fares.json": fares,
        "train_capacities.json": capacities,
        "seats.json": seats,
        "passengers.json": passengers,
        "bookings.json": bookings,
        "booking_travellers.json": travellers,
        "service_cancellations.json": service_cancellations,
        "edge_cases.json": edge_cases,
    }
    for filename, value in files.items():
        _json_dump(output_dir / filename, value)

    manifest = {
        "dataset_id": DATASET_ID,
        "reference_date": reference_date.isoformat(),
        "random_seed": seed,
        "generated_at": datetime.now(IST).isoformat(),
        "creative_generation": creative_generation,
        "files": sorted(files),
        "counts": {
            "stations": len(stations),
            "trains": len(trains),
            "train_stops": len(train_stops),
            "fares": len(fares),
            "train_capacities": len(capacities),
            "seats": len(seats),
            "passengers": len(passengers),
            "bookings": len(bookings),
            "booking_travellers": len(travellers),
            "service_cancellations": len(service_cancellations),
        },
    }
    _json_dump(output_dir / "generation_manifest.json", manifest)
    return manifest
