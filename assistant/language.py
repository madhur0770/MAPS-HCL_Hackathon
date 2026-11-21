"""Detect the language of the passenger's message: en, hi (Devanagari) or hinglish (Hindi in Roman letters)."""
import re

HINGLISH_WORDS = set("""kal parso aaj kitna kitni kitne paisa paise wapas kya hai hain mera meri mere nahi nahin kaise kab kahan
ticket cancel karo karna kar karni chahiye chahta chahti sakta sakte sakti badal badlein badalna se tak ko ka ki ke mein me
bhai ji haan han theek thik batao bataiye dikhao dikha lagta lagega milega milta gaadi gadi train kitne bachche saaman
abhi pehle baad subah shaam raat din tarikh seat berth konsi konsa koi""".split())


def detect(text: str) -> str:
    if re.search(r"[ऀ-ॿ]", text):
        return "hi"
    words = re.findall(r"[a-z]+", text.lower())
    if not words:
        return "en"
    hits = sum(1 for w in words if w in HINGLISH_WORDS and w not in ("train", "ticket", "cancel", "seat", "berth", "me", "ko", "ki"))
    strong = sum(1 for w in words if w in ("kal", "parso", "kitna", "kitni", "paisa", "paise", "wapas", "kya", "mera", "meri", "nahi", "kaise", "karo", "chahiye", "sakta", "badlein", "badal", "milega", "lagega", "batao", "hai", "hain", "se"))
    if strong >= 1 and hits >= 2 or strong >= 2:
        return "hinglish"
    return "en"
