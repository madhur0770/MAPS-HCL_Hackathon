"""Turn words like 'tomorrow', 'kal', 'parso', '24 Nov', '24/11' into a date, relative to as_of."""
import datetime as dt
import re

MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}
MONTHS.update({"january": 1, "february": 2, "march": 3, "april": 4, "june": 6, "july": 7, "august": 8,
               "september": 9, "sept": 9, "october": 10, "november": 11, "december": 12})
WEEKDAYS = {"monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "wednesday": 2, "wed": 2, "thursday": 3, "thu": 3,
            "friday": 4, "fri": 4, "saturday": 5, "sat": 5, "sunday": 6, "sun": 6}


def parse_date(text: str, as_of: dt.datetime):
    """Returns (date or None, label). Never guesses when the words are not clear."""
    t = text.lower()
    today = as_of.date()
    t = re.sub(r"\b(tomorow|tommorow|tomorrrow|tommorrow|tomoro|tomorow|tmr|tmrw|tmw|2morrow|2moro)\b", "tomorrow", t)
    t = re.sub(r"\b(todya|toady|todai|tody)\b", "today", t)
    if re.search(r"\b(day after tomorrow|parso|parson)\b|परसों", t):
        return today + dt.timedelta(days=2), "day after tomorrow"
    if re.search(r"\b(tomorrow|tmrw|kal)\b|कल", t) and not re.search(r"\bkal (se|tak) pehle\b", t):
        return today + dt.timedelta(days=1), "tomorrow"
    if re.search(r"\b(today|aaj|aj)\b|आज", t):
        return today, "today"
    m = re.search(r"\b(20\d\d)-(\d{1,2})-(\d{1,2})\b", t)
    if m:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))), "iso"
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s+)?(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b(?:\s*,?\s*(20\d\d))?", t)
    if m:
        d, mo = int(m.group(1)), MONTHS[m.group(2)]
        y = int(m.group(3)) if m.group(3) else today.year
        try:
            r = dt.date(y, mo, d)
            if not m.group(3) and r < today - dt.timedelta(days=1):
                r = dt.date(y + 1, mo, d)
            return r, "date"
        except ValueError:
            return None, "bad"
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\b", t)
    if m:
        mo, d = MONTHS[m.group(1)], int(m.group(2))
        try:
            r = dt.date(today.year, mo, d)
            if r < today - dt.timedelta(days=1):
                r = dt.date(today.year + 1, mo, d)
            return r, "date"
        except ValueError:
            return None, "bad"
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](20\d\d))?\b", t)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        y = int(m.group(3)) if m.group(3) else today.year
        try:
            return dt.date(y, mo, d), "date"
        except ValueError:
            return None, "bad"
    m = re.search(r"\b(?:next |this |on )?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", t)
    if m:
        wd = WEEKDAYS[m.group(1)]
        delta = (wd - today.weekday()) % 7
        if delta == 0 or "next" in m.group(0):
            delta = delta or 7
        return today + dt.timedelta(days=delta), "weekday"
    return None, "none"
