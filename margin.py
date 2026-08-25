"""Combineert een Troostwijk-kavel met een 2dehands-prijsschatting tot een marge-score.

Een automatische zoekterm kan altijd een keer misgrijpen (een te generieke term matcht iets
compleet anders). Bij kavels met veel stuks wordt zo'n misgreep in de mediaanprijs vermenigvuldigd
tot een absurd groot getal. Daarom krijgt elk resultaat ook een betrouwbaarheidslabel + een
steekproef van de gevonden 2dehands-listings, zodat je bij twijfel zelf kan controleren of de
match uberhaupt ergens op slaat voor je een bod overweegt."""

from dataclasses import dataclass, field
from typing import List

from filters import Lot

MIN_CONFIDENT_N = 8
MAX_PLAUSIBLE_RATIO = 15.0  # verkoopwaarde/stuk vs kostprijs/stuk -- hoger is verdacht
MIN_QUERY_WORDS_FOR_TRUST = 2  # 1 los, kort woord ("M8", "plus") is vaak te generiek
SHORT_WORD_LEN = 5


@dataclass
class MarginResult:
    lot: Lot
    quantity: int
    allin_cost_eur: float
    resale_query: str
    resale_median_eur: float
    resale_n: int
    total_resale_value_eur: float
    margin_eur: float
    roi_multiple: float  # verkoopwaarde / all-in kostprijs
    confidence: str  # "hoog" of "laag"
    confidence_reason: str
    sample_listings: List[str] = field(default_factory=list)


def _assess_confidence(resale_n: int, query: str, per_unit_cost: float, per_unit_resale: float) -> tuple:
    reasons = []
    query_words = query.split()
    if resale_n < MIN_CONFIDENT_N:
        reasons.append(f"weinig 2dehands-resultaten (n={resale_n})")
    if len(query_words) < MIN_QUERY_WORDS_FOR_TRUST and len(query) <= SHORT_WORD_LEN:
        reasons.append(f"zoekterm te kort/generiek ('{query}')")
    if per_unit_cost > 0:
        ratio = per_unit_resale / per_unit_cost
        if ratio > MAX_PLAUSIBLE_RATIO:
            reasons.append(f"verkoopwaarde/stuk is {ratio:.0f}x de kostprijs/stuk -- onwaarschijnlijk hoog")

    if reasons:
        return "laag", "; ".join(reasons)
    return "hoog", ""


def compute_margin(
    lot: Lot,
    quantity: int,
    resale_median_eur: float,
    resale_n: int,
    resale_query: str,
    sample_listings: List[str] = None,
    extra_cost_pct: float = 0.19,
) -> MarginResult:
    allin_cost = lot.current_bid_eur * (1 + extra_cost_pct)
    total_resale_value = resale_median_eur * quantity
    margin = total_resale_value - allin_cost
    roi = total_resale_value / allin_cost if allin_cost > 0 else float("inf")

    per_unit_cost = allin_cost / quantity if quantity else allin_cost
    confidence, reason = _assess_confidence(resale_n, resale_query, per_unit_cost, resale_median_eur)

    return MarginResult(
        lot=lot,
        quantity=quantity,
        allin_cost_eur=allin_cost,
        resale_query=resale_query,
        resale_median_eur=resale_median_eur,
        resale_n=resale_n,
        total_resale_value_eur=total_resale_value,
        margin_eur=margin,
        roi_multiple=roi,
        confidence=confidence,
        confidence_reason=reason,
        sample_listings=sample_listings or [],
    )
