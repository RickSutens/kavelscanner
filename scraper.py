"""Haalt kaveldata op van Troostwijk Auctions via de __NEXT_DATA__ JSON die elke pagina meestuurt.
Geen ongedocumenteerde/private endpoints, geen inloggen nodig -- gewoon dezelfde pagina's die een
bezoeker ook ziet, uitgelezen als data i.p.v. als HTML."""

import json
import re
import time
import urllib.request
from typing import Dict, List, Optional

from filters import Lot

USER_AGENT = "kavelscanner-personal-tool/0.1"
BASE_URL = "https://www.troostwijkauctions.com"


def _fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def _extract_next_data(html: str) -> dict:
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not match:
        raise ValueError("Kon __NEXT_DATA__ niet vinden in de pagina -- structuur van de site kan gewijzigd zijn")
    return json.loads(match.group(1))


def fetch_menu_categories() -> List[dict]:
    """Haalt de lijst van hoofdcategorieën (met slug/id) op via de homepage."""
    html = _fetch_html(f"{BASE_URL}/nl")
    props = _extract_next_data(html)["props"]["pageProps"]
    return props["menuCategories"]


def fetch_category_page(
    category_path: str,
    radius: Optional[str],
    page: int,
    page_size: int = 48,
    sorting: Optional[str] = None,
) -> dict:
    """category_path bv. 'bouw-en-grondverzet/f77365fe-eaa8-42d1-97fc-b14d0111160c'."""
    url = f"{BASE_URL}/nl/c/{category_path}?page={page}&pageSize={page_size}"
    if radius:
        url += f"&radius={radius}"
    if sorting:
        url += f"&sorting={sorting}"
    html = _fetch_html(url)
    return _extract_next_data(html)["props"]["pageProps"]


def fetch_lot_detail(lot_url: str) -> dict:
    """Haalt de losse kavelpagina op (bv. https://www.troostwijkauctions.com/l/...-A1-48676-2).

    Bevat o.a. 'quantity' (aantal stuks) en 'categoryBreadcrumbs', die niet in de
    categorie-lijstweergave zitten."""
    html = _fetch_html(lot_url)
    return _extract_next_data(html)["props"]["pageProps"]


def fetch_category_lots(
    category_path: str,
    category_label: str,
    radius: str,
    max_pages: Optional[int] = None,
    delay_sec: float = 1.5,
) -> List[Lot]:
    """Haalt alle kavels van 1 categorie op (al server-side gefilterd op radius door Troostwijk zelf)."""
    lots: List[Lot] = []
    page = 1
    while True:
        props = fetch_category_page(category_path, radius, page)
        lots_data = props["lotsData"]
        results = lots_data["results"]
        total = lots_data["totalSize"]

        for raw in results:
            lots.append(
                Lot(
                    id=raw["displayId"],
                    title=raw["title"],
                    category=category_label,
                    city=raw["location"]["city"],
                    country_code=raw["location"]["countryCode"],
                    opening_bid_eur=None,
                    current_bid_eur=raw["currentBidAmount"]["cents"] / 100,
                    end_date=raw["endDate"],
                    url=f"{BASE_URL}/l/{raw['urlSlug']}",
                    quantity=1,
                )
            )

        if max_pages and page >= max_pages:
            break
        if page * page_size >= total:
            break
        page += 1
        time.sleep(delay_sec)  # niet agressief bevragen

    return lots
