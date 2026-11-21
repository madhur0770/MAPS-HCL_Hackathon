"""Turn a message into {intent, slots}. Keyword and pattern rules in English, Hindi and Hinglish (fast, testable).
If the rules cannot decide, an optional language model may suggest an intent (checked against a fixed list)."""
import re

from assistant import dates
from tools import timetable as tt

INTENTS = ["privacy_ask", "greet", "my_bookings", "booking_status", "refund_estimate", "cancel_request", "change_boarding", "book_ticket",
           "deadline", "search_trains", "seats", "fare", "rules", "handoff_request", "dispute", "forbidden", "unknown"]

R = lambda p: re.compile(p, re.I)  # noqa: E731
CANCEL = r"(cancel|cancell|radd|रद्द|कैंसिल|cancle|kaato|हटा)"
REFUND = r"(refund|wapas|वापस|paisa|paise|पैसा|पैसे|get back|money back|रिफंड|milega|मिलेगा|milenge)"
HOWMUCH = r"(how much|kitna|kitne|kitni|कितना|कितने|कितनी|what (will|would) i get|estimate|if i cancel|agar|अगर|what if)"

P = {
 "forbidden": [
   R(r"(give me (a |the )?(full|complete|100%|poora) refund|\bwaive\b|exception|bend the rules|make an exception|extra refund|full refund anyway|refund (more|above|extra)|more than (the )?(rule|policy)|zyada refund|poora refund de do|charge (hata|mat|waive))"),
   R(r"(jump|skip|move (me|my|it)|push (me|my)|ahead of|upar kar|aage kar|confirm kar do|confirm my waitlist|waiting? ?list.*(confirm|upar|jump|ahead))"),
   R(r"(change|lower|reduce|decrease|kam kar|badal).{0,20}(the )?(fare|kiraya|price)|fare.{0,15}(change|kam|lower|reduce|discount)|discount de do"),
   R(r"(cancel|change|show|see|dikha|check).{0,30}(someone else|somebody|my (friend|brother|sister|colleague|neighbou?r|boss|wife|husband)|his|her|their|kisi aur|dost|bhai|behen|padosi)(.{0,15}(booking|ticket))?"),
 ],
 "dispute": [
   R(r"(missed|miss (my|the)|chhoot gayi|chut gayi|छूट गई|train miss|late (to|for) the train)"),
   R(r"(refund (dispute|not (received|credited)|didn.?t (come|arrive))|not got my refund|wrong refund|system error|double charged|charged twice|complain|complaint|शिकायत|shikayat|galat refund|refund nahi aaya|refund nahi mila)"),
   R(r"(disab|handicap|divyang|press (card|quota)|defence|defense|army|veteran|concession (for|with|needs?)|medical concession|concession.{0,25}(proof|certificate)|(proof|certificate).{0,25}concession)"),
 ],
 "handoff_request": [R(r"(human|agent|real person|desk|supervisor|manager|insaan|kisi se baat|बात करनी|इंसान|मानव|speak to someone|talk to someone)")],
 "my_bookings": [R(r"(my bookings|all (my )?bookings|list (my )?bookings|show (me )?(my )?bookings|meri (saari )?bookings?|मेरी (सभी )?बुकिंग|booking list|my tickets|meri tickets?)")],
 "greet": [R(r"^\s*(hi|hello|hey|namaste|namaskar|hii+|नमस्ते|नमस्कार|good (morning|evening|afternoon))\b[\s!.]*$")],
 "deadline": [R(r"(last (date|time|day)|until when|till when|by when|deadline|cut-?off|kab tak|कब तक|antim|अंतिम|how late|how long before|time limit)")],
 "change_boarding": [R(r"((change|badal|बदल|switch|shift|move).{0,25}(boarding|board|station|स्टेशन)|(boarding|board).{0,25}(change|badal|बदल))")],
 "book_ticket": [R(r"(\bbook\b|reserve|bukk|बुक|buking|i want a ticket|ticket chahiye|ticket book|टिकट चाहिए)")],
 "booking_status": [R(r"(status|pnr|my booking|meri booking|मेरी बुकिंग|confirm (hua|ho gaya|hai)|booking (check|details|kya)|waiting list (status|position)|berth|coach|seat number|kaunsa seat)")],
 "seats": [R(r"(seats?|availab|berth|rac|waiting ?list|wl\b|vacant|khaali|खाली|सीट)")],
 "fare": [R(r"(fare|kiraya|किराया|ticket price|price of|cost of|how much (is|does|for).{0,25}(ticket|train|2a|3a|sl|1a)|kitna lagega)")],
 "search_trains": [R(r"(train|trains|gaadi|गाड़ी|ट्रेन|timetable|schedule|departure|arrival|timing|chalti|कब चलती)")],
 "rules": [R(r"(kitne (ghante|din|minute)|hoti hai|hota hai|hote hain|kya hai|kaise|kya main|kya mai|kab (khul|band)|\bkhulti|\bband hoti|\bkitna|rule|policy|allowed|permitted|can i (carry|take|bring)|how many|charge|charges|tatkal|तत्काल|luggage|saaman|सामान|pet|child|children|bachche|senior|concession|chart|rac|waiting|clerkage|waiver|circular|faq|notice|कितना|नियम|rules?)")],
}

CLASS_RE = R(r"\b(fp|first premium|ac ?2( tier)?|2a|2ac|2 tier|ac ?3( tier)?|3a|3ac|3 tier|ec|executive chair|sl|sleeper|slpr|cc|city chair)\b")
BK_RE = R(r"\b([A-Z]{2,4})\s?-?\s?(\d{3,8})\b")      # any booking-reference style: BKG0001, UR-48213 ... (checked against the data below)
TRAIN_RE = re.compile(r"\b(UJ\s?-?\d{4})\b", re.I)
ACT_RE = re.compile(r"\bACT-[A-Z0-9]{8}\b")
CLASS_MAP = {"fp": "FP", "first premium": "FP", "ac2": "AC2", "ac 2": "AC2", "ac2 tier": "AC2", "ac 2 tier": "AC2", "2a": "AC2", "2ac": "AC2", "2 tier": "AC2",
             "ac3": "AC3", "ac 3": "AC3", "ac3 tier": "AC3", "ac 3 tier": "AC3", "3a": "AC3", "3ac": "AC3", "3 tier": "AC3",
             "ec": "EC", "executive chair": "EC", "sl": "SL", "sleeper": "SL", "slpr": "SL", "cc": "CC", "city chair": "CC"}


_cache = {}


def _known(db):
    """Train numbers, booking ids and class codes that really exist in the data (so new test data works without code changes)."""
    key = id(db)
    n = db.execute("SELECT count(*) FROM trains").fetchone()[0] + db.execute("SELECT count(*) FROM bookings").fetchone()[0]
    c = _cache.get(key)
    if c and c[0] == n:
        return c[1]
    trains = [r[0] for r in db.execute("SELECT train_no FROM trains")]
    bids = {r[0] for r in db.execute("SELECT booking_id FROM bookings")}
    classes = set()
    for r in db.execute("SELECT classes FROM trains"):
        classes |= {x.strip() for x in (r[0] or "").split(",") if x.strip()}
    val = {"trains": trains, "bids": bids, "classes": classes}
    _cache[key] = (n, val)
    return val


def find_train(db, text):
    for no in _known(db)["trains"]:
        letters, digits = re.match(r"^(\D*)(\d.*)$", no).groups() if re.match(r"^\D*\d", no) else (no, "")
        pat = r"\b%s[\s-]?%s\b" % (re.escape(letters), re.escape(digits)) if letters else r"\b%s\b" % re.escape(digits)
        if re.search(pat, text, re.I):
            return no
    return None


def find_booking_ref(db, text, train_no=None):
    """A booking reference written like XXX-1234 / XXX1234. Prefer one that exists; otherwise return the first candidate (it will be refused as 'not yours')."""
    k = _known(db)
    first = None
    for m in BK_RE.finditer(text):
        pre, num = m.group(1).upper(), m.group(2)
        if pre == "ACT" or (pre + num) == (train_no or ""):
            continue
        if any(pre + num == tn or pre + "-" + num == tn for tn in k["trains"]):
            continue
        for cand in (pre + num, pre + "-" + num):
            if cand in k["bids"]:
                return cand
        if first is None and pre not in ("AC", "SL", "CC", "EC", "FP", "UJ") and pre not in ("RS", "INR", "KG"):
            first = (pre + "-" + num) if pre == "UR" else (pre + num)
    return first


def norm_class(s):
    return CLASS_MAP.get(re.sub(r"\s+", " ", s.lower()).strip())


_BLACK = set("tomorrow today kal aaj parso day after monday tuesday wednesday thursday friday saturday sunday next on book booking ticket tickets train to from on for of the and aur names name travellers traveller passengers passenger "
             "age aged years year yrs old class sl 3a 2a 1a with please need want pune nagpur".split())


def extract_travellers(db, text):
    """Pairs like 'Aarav 34, Neha 31'. Only the last words before a number count as the name."""
    skip = set(tt.station_index(db).keys()) | set(dates.MONTHS.keys()) | _BLACK
    out = []
    for chunk in re.split(r"[,;\n]|\band\b|\baur\b", text):
        m = re.search(r"([A-Za-z\u0900-\u097F]+(?: [A-Za-z\u0900-\u097F]+){0,2})\s*[:\-(]?\s*(?:aged?\s*)?(\d{1,3})\s*(?:yrs?|years?|saal|साल)?\)?\s*$", chunk.strip(), re.I)
        if not m:
            continue
        words = m.group(1).split()
        while words and words[0].lower() in skip:
            words.pop(0)
        words = [w for w in words if w.lower() not in _BLACK]
        age = int(m.group(2))
        if words and 0 < age < 110 and not re.match(r"(?i)^(bk|act)\d", words[0]):
            out.append({"name": " ".join(words).title(), "age": age})
    return out


def understand(db, text: str, as_of, session_slots=None):
    t = text.strip()
    slots = {}
    tn = find_train(db, t)
    if tn:
        slots["train_no"] = tn
    ref = find_booking_ref(db, t, tn)
    if ref:
        slots["booking_id"] = ref
    m = ACT_RE.search(t)
    if m:
        slots["action_id"] = m.group(0)
    m = CLASS_RE.search(t)
    if m:
        slots["class"] = norm_class(m.group(1))
    else:   # any class code that exists in the data (e.g. a new class added to the test data)
        for w in re.findall(r"\b[A-Za-z0-9]{1,4}\b", t):
            if w.upper() in _known(db)["classes"]:
                slots["class"] = w.upper()
                break
    d, _ = dates.parse_date(t, as_of)
    if d:
        slots["date"] = d.isoformat()
    st = tt.find_stations_in(db, t)
    if st:
        slots["stations"] = st
    trs = extract_travellers(db, t)
    if trs:
        slots["travellers"] = trs
    low = t.lower()

    def has(intent):
        return any(p.search(t) for p in P[intent])

    cancel_w = bool(re.search(CANCEL, t, re.I))
    refund_w = bool(re.search(REFUND, t, re.I))
    howmuch = bool(re.search(HOWMUCH, t, re.I))

    if re.search(r"\b(phone|mobile|contact number|aadhaar|aadhar|passport|pan card|id number|home address)\b|फ़ोन|मोबाइल|आधार", t, re.I) and re.search(r"\b(number|passenger|his|her|their|[A-Z][a-z]+'s|of|ka|ki)\b|नंबर", t):
        intent = "privacy_ask"
    elif re.search(r"\b(hotel|hotels|flight|flights|cab|taxi|restaurant|bus ticket|movie|weather|visa|cricket|stock|recipe|pizza|resort|room booking)\b", t, re.I) and not slots.get("booking_id"):
        intent = "unknown"
    elif has("forbidden"):
        intent = "forbidden"
    elif has("dispute"):
        intent = "dispute"
    elif has("handoff_request"):
        intent = "handoff_request"
    elif has("greet"):
        intent = "greet"
    elif has("my_bookings") and not slots.get("booking_id"):
        intent = "my_bookings"
    elif has("deadline"):
        intent = "deadline"
    elif cancel_w and (refund_w or howmuch) and re.search(r"(how much|kitna|kitne|कितना|estimate|what (will|would)|if i|agar|अगर|what if|milega|मिलेगा|milenge)", t, re.I):
        intent = "refund_estimate"
    elif cancel_w and not slots.get("booking_id") and re.search(r"\b(what('s| is| are)?|is there|are there|does|do you|any|charges?|fees?|policy|rules?|why|when|how|kya hai|क्या|कितना|kitna)\b|क्या|कितना", t, re.I) and not re.search(r"\b(cancel|cancel karo|radd karo)\b (my|the|this|it|booking|ticket)", t, re.I):
        intent = "rules"
    elif cancel_w and not re.search(r"\b(train|trains|gaadi)\b.*\b(cancelled|cancel hui|cancel ho gayi)\b", low):
        intent = "cancel_request"
    elif refund_w and slots.get("booking_id"):
        intent = "refund_estimate"
    elif has("change_boarding"):
        intent = "change_boarding"
    elif has("book_ticket") and not has("booking_status") and not slots.get("booking_id") and not (
            re.search(r"^\s*(how|what|when|can|could|is|are|do|does|which|kitne|kab|kya|kaise)\b", t, re.I) and not slots.get("stations") and not slots.get("travellers")
            and not slots.get("date") and not slots.get("class")):
        intent = "book_ticket"
    elif has("booking_status") or (slots.get("booking_id") and not has("search_trains")):
        intent = "booking_status"
    elif has("fare") and len(slots.get("stations", [])) >= 2:
        intent = "fare"
    elif len(slots.get("stations", [])) >= 2 and has("seats"):
        intent = "seats"
    elif len(slots.get("stations", [])) >= 2 or (has("search_trains") and slots.get("stations")):
        intent = "search_trains"
    elif has("seats") and slots.get("train_no"):
        intent = "seats"
    elif has("rules"):
        intent = "rules"
    elif has("fare"):
        intent = "fare"
    elif has("search_trains"):
        intent = "search_trains"
    else:
        intent = "unknown"
    # topic hint for the document search
    topic = None
    for rx, tp in ((r"tatkal|तत्काल", "tatkal"), (r"\bpets?\b|\bdogs?\b|\bcats?\b|पालतू|assistance animal|kutta|kutte", "pets"),
                   (r"luggage|baggage|saaman|सामान|excess weight", "luggage"),
                   (r"\bid proof|identity|\bid\b|aadhaar|passport|photo id|verification|पहचान", "identity"),
                   (r"child|children|bachche|senior|concession|student|discount|बच्चे|बुज़ुर्ग|छूट", "concession"),
                   (r"train (was |is |has been )?cancel|delay|late by|cancelled by|operator cancel|train cancel|delayed|गाड़ी रद्द|देरी", "disruption"),
                   (r"waiting|waitlist|\bwl\b|\brac\b|promot|clerkage|वेटिंग", "waitlist"),
                   (r"boarding|board", "boarding_change"),
                   (r"refund|cancel|charge|wapas|radd|रद्द|वापस|पैसा|paisa|fixed charge", "refund"),
                   (r"complain|complaint|harass|safety|shikayat|शिकायत", "complaints"),
                   (r"open|opens|close|closes|advance|how early|book(ing)? window|kitne din pehle|band hoti|traveller limit|how many (travellers|passengers)|kitne (travellers|yatri|passengers|log)", "booking"),
                   (r"\bclass(es)?\b|\bfp\b|\bec\b|\bcc\b|first premium|executive chair|city chair", "classes")):
        if re.search(rx, t, re.I):
            topic = tp
            break
    slots["topic"] = topic
    return {"intent": intent, "slots": slots}
