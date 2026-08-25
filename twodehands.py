"""Haalt zoekresultaten + mediaanprijs op van 2dehands.be voor een zoekterm.

Gebruikt alleen de normale, publiek toegankelijke zoekresultatenpagina (/q/{term}/), NIET de
interne API-endpoints (/lrp/api/search*, /v/api/*) die 2dehands zelf in robots.txt blokkeert
voor crawlers. De pagina bevat dezelfde data als ingebouwde __NEXT_DATA__ JSON."""

import json
import re
import statistics
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import List, Optional

from query_normalize import query_candidates

USER_AGENT = "kavelscanner-personal-tool/0.1"
BASE_URL = "https://www.2dehands.be"
DELAY_SEC = 1.2

# priceType-waarden die een echte prijs vertegenwoordigen (SEE_DESCRIPTION/GRATIS/etc. hebben priceCents=0)
PRICED_TYPES = {"FIXED", "MIN_BID", "NEGOTIABLE"}


@dataclass
class Listing:
    item_id: str
    title: str
    price_eur: float
    price_type: str
    city: str
    url: str


def _fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def _extract_next_data(html: str) -> dict:
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not match:
        raise ValueError("Kon __NEXT_DATA__ niet vinden -- structuur van 2dehands.be kan gewijzigd zijn")
    return json.loads(match.group(1))


def fetch_listings(query: str, max_pages: int = 2) -> List[Listing]:
    """Haalt tot max_pages paginas zoekresultaten op voor een zoekterm."""
    encoded = urllib.parse.quote(query.strip())
    listings: List[Listing] = []

    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/q/{encoded}/" if page == 1 else f"{BASE_URL}/q/{encoded}/p/{page}/"
        html = _fetch_html(url)
        data = _extract_next_data(html)
        sr = data["props"]["pageProps"].get("searchRequestAndResponse")
        if not sr:
            break

        for raw in sr.get("listings", []):
            price_info = raw.get("priceInfo", {})
            listings.append(
                Listing(
                    item_id=raw["itemId"],
                    title=raw["title"],
                    price_eur=price_info.get("priceCents", 0) / 100,
                    price_type=price_info.get("priceType", ""),
                    city=raw.get("location", {}).get("cityName", ""),
                    url=f"{BASE_URL}{raw.get('vipUrl', '')}",
                )
            )

        total = sr.get("totalResultCount", 0)
        if page * 30 >= total:  # 2dehands toont doorgaans ~30 resultaten/pagina
            break
        time.sleep(DELAY_SEC)

    return listings


def estimate_resale_value(
    lot_title: str, min_results: int = 5, max_pages: int = 2
) -> Optional[dict]:
    """Probeert de zoektermladder (specifiek -> generiek) tot er genoeg geprijsde resultaten zijn.

    Geeft None terug als zelfs de generieke term niks bruikbaars oplevert.
    """
    best = None
    for query in query_candidates(lot_title):
        listings = fetch_listings(query, max_pages=max_pages)
        priced = [l for l in listings if l.price_type in PRICED_TYPES and l.price_eur > 0]

        if best is None or len(priced) > len(best["listings"]):
            best = {"query_used": query, "listings": priced}

        if len(priced) >= min_results:
            break
        time.sleep(DELAY_SEC)

    if best is None or not best["listings"]:
        return None

    prices = [l.price_eur for l in best["listings"]]
    return {
        "query_used": best["query_used"],
        "median_eur": statistics.median(prices),
        "mean_eur": statistics.mean(prices),
        "n": len(prices),
        "listings": best["listings"],
    }
