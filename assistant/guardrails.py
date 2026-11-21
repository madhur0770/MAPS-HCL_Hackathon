"""Input and output guards. Text from users and from documents is DATA, never an order."""
import re

PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")
AADHAAR = re.compile(r"(?<!\d)\d{4}\s?\d{4}\s?\d{4}(?!\d)")
PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
CARD = re.compile(r"(?<!\d)(?:\d[ -]?){13,16}(?!\d)")
SECRET = re.compile(r"(sk-[A-Za-z0-9]{16,}|api[_-]?key\s*[:=]\s*\S+|password\s*[:=]\s*\S+|-----BEGIN [A-Z ]+KEY-----)", re.I)

INJECTION = [
    r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|rules|prompts?)",
    r"disregard (all |any |the )?(previous|prior|above|earlier|your) (instructions|rules)",
    r"you are now\b", r"act as (an? )?(admin|administrator|root|system|developer|different)",
    r"(reveal|show|print|repeat|leak) (me )?(your |the )?(system |hidden |initial )?(prompt|instructions)",
    r"\bsystem\s*:", r"\bdeveloper mode\b", r"\bjailbreak\b", r"override (the )?(rules|policy|policies|refund|limit)",
    r"(skip|bypass|without) (the )?(confirm|confirmation|preview)", r"pre-?authori[sz]ed",
    r"\bsudo\b", r"</?(system|assistant|instructions?)>", r"new instructions?\s*:",
    r"पिछले (सभी )?निर्देश(ों)? (को )?(अनदेखा|भूल)", r"pichhle (saare )?(instructions|nirdesh) (ignore|bhul)",
]
INJ_RE = re.compile("|".join(INJECTION), re.I)


def mask(text: str) -> str:
    """Replace sensitive numbers so they never reach logs."""
    t = SECRET.sub("[SECRET]", text)
    t = AADHAAR.sub("[ID]", t)
    t = PAN.sub("[ID]", t)
    t = CARD.sub("[CARD]", t)
    t = PHONE.sub(lambda m: "XXXXXX" + re.sub(r"\D", "", m.group())[-4:], t)
    return t


def has_secret(text: str) -> bool:
    return bool(SECRET.search(text))


def injection_found(text: str):
    m = INJ_RE.search(text)
    return m.group(0) if m else None


def strip_injection(text: str) -> str:
    """Remove the injected instruction so the rest of the question can still be answered."""
    return INJ_RE.sub(" ", text)


def wrap_untrusted(text: str, label="document") -> str:
    return "<untrusted %s>\n%s\n</untrusted %s>" % (label, text, label)


def output_guard(answer: str, own_last4=None):
    """Mask any full phone/ID number in a reply. Returns (clean_text, violations)."""
    v = []
    clean = answer
    for rx, name in ((AADHAAR, "id_number"), (PAN, "id_number"), (PHONE, "phone")):
        for m in rx.finditer(clean):
            v.append(name)
        clean = rx.sub(lambda m: "XXXXXX" + re.sub(r"\D", "", m.group())[-4:] if rx is PHONE else "[ID hidden]", clean)
    return clean, v
