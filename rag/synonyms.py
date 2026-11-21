"""Hindi / Hinglish words mapped to the English words our documents use (so search works in all 3 languages)."""
SYN = {
    "refund": ["refund", "paisa", "paise", "wapas", "वापस", "पैसा", "पैसे", "रिफंड", "return"],
    "cancel": ["cancel", "radd", "रद्द", "कैंसिल", "cancellation", "canceled", "cancelled"],
    "cancellation": ["cancel", "cancellation"],
    "boarding": ["boarding", "station", "badal", "badlein", "badalna", "बदलें", "बदलना", "स्टेशन"],
    "waitlist": ["waitlist", "waiting", "wl", "वेटिंग", "प्रतीक्षा"],
    "tatkal": ["tatkal", "तत्काल", "तत्काळ"],
    "luggage": ["luggage", "saaman", "samaan", "baggage", "सामान", "वज़न"],
    "pet": ["pet", "pets", "dog", "cat", "कुत्ता", "पालतू"],
    "child": ["child", "children", "kid", "bachche", "bachcha", "बच्चे", "बच्चा"],
    "senior": ["senior", "elderly", "बुज़ुर्ग", "वरिष्ठ"],
    "concession": ["concession", "discount", "chhoot", "छूट"],
    "rac": ["rac"],
    "chart": ["chart"],
    "charge": ["charge", "charges", "shulk", "शुल्क", "katega", "kate", "कटेगा"],
    "fare": ["fare", "kiraya", "kiraye", "किराया", "किराये", "price", "cost"],
    "train": ["train", "gaadi", "gadi", "ट्रेन", "गाड़ी"],
    "missed": ["missed", "miss", "chhoot", "chhut", "छूट"],
    "privacy": ["privacy", "private", "data"],
}
_REV = {}
SYN = {k: [x.rstrip("s") if x.isascii() and len(x) > 3 and not x.endswith("ss") else x for x in v] for k, v in SYN.items()}
for canon, words in SYN.items():
    for w in words:
        _REV.setdefault(w, set()).add(canon)


def expand(tokens):
    out = list(tokens)
    for t in tokens:
        for canon in _REV.get(t, ()):
            if canon not in out:
                out.append(canon)
            # also add the canonical word's plain-English siblings that documents use
            for w in SYN.get(canon, ())[:1]:
                if w not in out:
                    out.append(w)
    return out
