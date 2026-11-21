"""Numbers come from here, valid for a given time (as_of). Never from the language model."""
import datetime as dt


def settings_at(db, as_of: dt.datetime) -> dict:
    """{name: (value, source_doc, section, effective_from)} - latest row whose effective_from <= as_of date."""
    d = as_of.date().isoformat()
    rows = db.execute("SELECT name,value,effective_from,source_doc,section FROM settings_history "
                      "WHERE effective_from<=? ORDER BY effective_from ASC, id ASC", (d,)).fetchall()
    out = {}
    for r in rows:
        out[r["name"]] = (r["value"], r["source_doc"], r["section"], r["effective_from"])
    return out


def get(db, name: str, as_of: dt.datetime):
    s = settings_at(db, as_of)
    return s[name][0] if name in s else None


def get_int(db, name, as_of, default=0):
    v = get(db, name, as_of)
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def source(db, name, as_of):
    s = settings_at(db, as_of)
    return (s[name][1], s[name][2]) if name in s else ("", "")
