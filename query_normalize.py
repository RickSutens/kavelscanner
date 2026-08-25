"""Zet een (vaak technische) Troostwijk-kaveltitel om in een reeks zoektermen voor 2dehands,
van specifiek naar generiek. Troostwijk-titels volgen vaak het patroon
'Merk Model specificaties Zelfstandignaamwoord (aantal/afmeting)' -- Nederlandse samenstellingen
staan meestal aan het eind van de titel, dus de laatste 1-2 woorden zijn typisch de generieke
productnaam die je ook op een tweedehands-marktplaats zou intikken."""

import re
from typing import List

_PAREN_RE = re.compile(r"\([^)]*\)")
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_NUMUNIT_RE = re.compile(
    r"\b\d+[.,]?\d*\s*(kg|kva|kw|hp|pk|ton|m³|m2|m²|mm|cm|km|hr|uur|liter|ltr|volt|v|a|w)\b",
    re.IGNORECASE,
)
_DIMENSION_RE = re.compile(
    r"\b\d+[.,]?\d*(?:\s*x\s*\d+[.,]?\d*)+\s*(?:mm|cm|m|kg|kva|kw|ton)?\b", re.IGNORECASE
)
_LONE_NUMBER_RE = re.compile(r"\b\d+[.,]?\d*\s*(meter|m)\b", re.IGNORECASE)
# Belgische/Nederlandse kentekenplaten, bv. "04-XP-SG" of "AB-123-C" -- laten anders vervuilde
# fragmenten als (zinloze) zoekterm achter.
_LICENSE_PLATE_RE = re.compile(r"\b[A-Z0-9]{1,3}-[A-Z0-9]{1,3}-[A-Z0-9]{1,3}\b")
_SEPARATORS_RE = re.compile(r"[/\-–,]")
_WHITESPACE_RE = re.compile(r"\s+")

# Woorden die op zichzelf te generiek/betekenisloos zijn om als zoekterm te eindigen
# (conditie-aanduidingen, Engelse restwoorden, modifiers die overal in voorkomen).
_FILLER_WORDS = {
    "car", "auto", "nieuw", "gebruikt", "plus", "set", "diversen", "overig", "overige",
    "outlet", "sale", "incl", "excl", "en", "of", "met", "voor", "type",
}


def clean_title(title: str) -> str:
    """Verwijdert bouwjaren, kentekens, aantallen/afmetingen en te generieke restwoorden."""
    t = title
    t = _LICENSE_PLATE_RE.sub(" ", t)
    t = _PAREN_RE.sub(" ", t)
    t = _YEAR_RE.sub(" ", t)
    t = _NUMUNIT_RE.sub(" ", t)
    t = _DIMENSION_RE.sub(" ", t)
    t = _LONE_NUMBER_RE.sub(" ", t)
    t = _SEPARATORS_RE.sub(" ", t)
    t = _WHITESPACE_RE.sub(" ", t).strip()

    words = [w for w in t.split() if w.lower() not in _FILLER_WORDS]
    return " ".join(words)


def query_candidates(title: str) -> List[str]:
    """Geeft zoektermen terug, van meest naar minst specifiek."""
    cleaned = clean_title(title)
    words = [w for w in cleaned.split() if w]

    candidates = []
    if cleaned:
        candidates.append(cleaned)
    for n in (3, 2, 1):
        if len(words) > n:
            candidates.append(" ".join(words[-n:]))

    seen = set()
    result = []
    for c in candidates:
        key = c.lower()
        if key and key not in seen:
            seen.add(key)
            result.append(c)
    return result
