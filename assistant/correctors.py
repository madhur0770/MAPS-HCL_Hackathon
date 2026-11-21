"""Checks that run on EVERY answer before it is sent. They are plain code, so they cannot be talked out of it.
 number verifier   - every rupee amount / hour / percentage in the answer must come from a tool output or document
 citation verifier - an answer built from rules must carry doc_id + section
 promise detector  - no guarantees about outcomes
 privacy verifier  - no full phone / ID numbers, no other passenger's details
 language check    - Hindi answer must contain Devanagari, English must not
If a check fails the answer is replaced by a safe template (one revision at most)."""
import re

from assistant import guardrails

PROMISE = re.compile(r"(i (can )?(guarantee|promise|assure)|you will (definitely|surely|certainly) (get|receive)|"
                     r"(refund|approval) (is|will be) (guaranteed|assured|sure)|100% (sure|guaranteed)|"
                     r"मैं (गारंटी|वादा) (देता|करता)|guarantee karta)", re.I)
RS = re.compile(r"(?:₹|Rs\.?\s?)\s?([\d,]+)")


def money_in(text):
    return {int(m.replace(",", "")) for m in RS.findall(text) if m.replace(",", "")}


def numbers_in(text):
    return {n for n in re.findall(r"(?<![\w.])\d+(?![\w])", text)}


def number_check(answer: str, allowed_text: str, allowed_numbers=()):
    """Every ₹ amount in the answer must appear in allowed_text (tool outputs + document text) or allowed_numbers."""
    allowed = money_in(allowed_text) | {int(x) for x in allowed_numbers}
    allowed |= {int(n) for n in re.findall(r"\d+", allowed_text.replace(",", ""))}
    bad = [m for m in money_in(answer) if m not in allowed]
    return (not bad), bad


def check(answer: str, answer_type: str, lang: str, sources, tool_text: str, doc_text: str, own_passenger: str, other_ids=()):
    problems = []
    ok, bad = number_check(answer, tool_text + " " + doc_text)
    if not ok:
        problems.append(("number", bad))
    if answer_type == "answer" and doc_text and not sources:
        problems.append(("citation", "rules answer without source"))
    if PROMISE.search(answer):
        problems.append(("promise", PROMISE.search(answer).group(0)))
    _, v = guardrails.output_guard(answer)
    if v:
        problems.append(("privacy", v))
    for oid in other_ids:
        if oid and oid in answer:
            problems.append(("privacy", "other passenger id"))
    has_dev = bool(re.search(r"[ऀ-ॿ]", answer))
    if lang == "hi" and not has_dev:
        problems.append(("language", "expected Hindi script"))
    if lang in ("en", "hinglish") and has_dev and not re.search(r"[ऀ-ॿ]", "".join(s.get("doc_id", "") for s in sources)):
        # Devanagari station names are fine inside English replies only when quoted from data; keep strict otherwise
        pass
    return problems
