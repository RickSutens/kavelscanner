"""Filters om kavels uit te sluiten op afstand tot ophaallocatie en op geschatte kostprijs."""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from distance import haversine_km
from geocode import geocode

# Coördinaten van Bree, Limburg, BE (via Troostwijk's eigen locatiezoeker opgezocht).
BREE_COORDS = (51.14109, 5.59762)

# Standaard opgeld/veilingkosten bij Troostwijk ligt meestal rond 15-19%.
DEFAULT_EXTRA_COST_PCT = 0.19

# Los bouwmateriaal/hardware -- lage waardedichtheid, geen interesse in doorverkoop.
EXCLUDE_KEYWORDS = [
    "schroef", "schroeven", "bout", "moer", "kartelmoer",
    "plank", "planken", "balk", "rabat", "steigerplank",
    "mdf", "plaat", "platen", "paneel", "panelen", "profiel",
    "glaswol", "isolatie", "steenwol",
]


def is_excluded_by_keyword(title: str, keywords: List[str] = EXCLUDE_KEYWORDS) -> bool:
    lower = title.lower()
    return any(kw in lower for kw in keywords)


@dataclass
class Lot:
    id: str
    title: str
    category: str
    city: str
    country_code: str
    current_bid_eur: float
    end_date: int  # unix timestamp
    url: str
    quantity: int = 1
    opening_bid_eur: Optional[float] = None


def within_distance(lot: Lot, origin: Tuple[float, float] = BREE_COORDS, max_km: float = 100.0) -> bool:
    """True als de ophaallocatie van de kavel binnen max_km van origin ligt."""
    lat, lon = geocode(lot.city, lot.country_code)
    return haversine_km(*origin, lat, lon) <= max_km


def within_budget(
    lot: Lot,
    extra_cost_pct: float = DEFAULT_EXTRA_COST_PCT,
    pickup_cost_eur: float = 0.0,
    max_total_eur: float = 500.0,
) -> bool:
    """True als de all-in kostprijs (huidig bod + opgeld/kosten + afhaalkosten) onder max_total_eur blijft.

    Gebruikt current_bid_eur (>= opening_bid_eur, want bieden gaat alleen omhoog) als
    strengste/actuele maatstaf.
    """
    total = lot.current_bid_eur * (1 + extra_cost_pct) + pickup_cost_eur
    return total <= max_total_eur


def screen_lots(
    lots: List[Lot],
    origin: Tuple[float, float] = BREE_COORDS,
    max_km: float = 100.0,
    extra_cost_pct: float = DEFAULT_EXTRA_COST_PCT,
    pickup_cost_eur: float = 0.0,
    max_total_eur: float = 500.0,
) -> List[Lot]:
    """Geeft de kavels terug die zowel de afstands- als de budgetfilter doorstaan."""
    passed = []
    for lot in lots:
        if is_excluded_by_keyword(lot.title):
            continue
        try:
            if not within_distance(lot, origin, max_km):
                continue
        except ValueError:
            continue  # locatie kon niet geocodeerd worden -> overslaan i.p.v. gokken
        if within_budget(lot, extra_cost_pct, pickup_cost_eur, max_total_eur):
            passed.append(lot)
    return passed
