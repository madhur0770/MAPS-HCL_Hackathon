"""Judges may load their own data: JSON or CSV, extra columns, different folder. Nothing in the code may name a station or a train."""
import csv, json, os, shutil
from core import db as dbm, official, seed
from tools import timetable as tt


def make_kit(tmp_path, as_csv):
    src = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data_kit", "data")
    dst = tmp_path / "kit"
    shutil.copytree(src, dst)
    syn = dst / "synthetic"
    # a tiny extra station with its own alias, plus an extra column the loader has never heard of
    st = json.load(open(syn / "stations.json", encoding="utf-8"))
    st.append({"dataset_id": "x", "station_code": "ZZZZ", "name": "Zebra Halt", "other_names": ["Zebra", "Zeebra Road"], "city": "Zebraville", "judge_note": "extra"})
    if as_csv:
        os.remove(syn / "stations.json")
        with open(syn / "stations.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["dataset_id", "station_code", "name", "other_names", "city", "judge_note"])
            for s in st:
                w.writerow([s["dataset_id"], s["station_code"], s["name"], json.dumps(s["other_names"]) if s["station_code"] == "ZZZZ" else ",".join(s["other_names"]).join(['"', '"']).strip('"'), s["city"], s.get("judge_note", "")])
    else:
        json.dump(st, open(syn / "stations.json", "w", encoding="utf-8"))
    return dst


def test_judge_data_json_with_extra_column_and_new_station(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_KIT_DIR", str(make_kit(tmp_path, False)))
    d = dbm.connect(":memory:"); seed.seed(d)
    assert tt.resolve_station(d, "Zeebra Road") == "ZZZZ"
    assert d.execute("SELECT count(*) FROM bookings").fetchone()[0] >= 50


def test_judge_data_csv_instead_of_json(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_KIT_DIR", str(make_kit(tmp_path, True)))
    d = dbm.connect(":memory:"); seed.seed(d)
    assert tt.resolve_station(d, "Zebra") == "ZZZZ" and tt.resolve_station(d, "Anand Pur Uttar") == "ANPN"
