"""STAP 1+2 scan: ELKE kavel die binnen CLOSING_WINDOW_DAYS sluit, voor ALLE hoofdcategorieen
(behalve Vastgoed), binnen 100km van Bree en onder EUR 500 all-in (bod + 19% opgeld).

Kavels die verder dan CLOSING_WINDOW_DAYS in de toekomst sluiten worden genegeerd -- daar kan
qua biedingen nog te veel veranderen om nu al zinvol te screenen. Categorieen worden gesorteerd
op sluitingstijd (oplopend) opgehaald, zodat we per categorie kunnen stoppen zodra we buiten het
venster vallen -- geen onnodige pagina's ophalen.

Schrijft alle geslaagde kavels naar een CSV in output/, en print alleen voortgang + samenvatting
naar de terminal (niet elke individuele kavel -- dat zou de terminal overspoelen)."""

import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from filters import Lot, screen_lots
from scraper import fetch_category_page, fetch_menu_categories

RADIUS = "Bree,51.14109,5.59762,100,BE"
SKIP_CATEGORIES = {"Vastgoed"}  # onroerend goed is niet herverkoopbaar als los item
PAGE_SIZE = 48
DELAY_SEC = 1.2
CLOSING_WINDOW_DAYS = 7
MAX_PAGES_PER_CATEGORY = 15  # veiligheidslimiet: voorkomt dat 1 drukke categorie de hele run vertraagt

OUTPUT_DIR = Path(__file__).parent / "output"


def scan_category(label: str, path: str, cutoff_ts: float) -> list:
    """Haalt kavels op (sluitingstijd oplopend) tot de eerste kavel voorbij cutoff_ts sluit."""
    lots = []
    page = 1
    while True:
        try:
            props = fetch_category_page(path, RADIUS, page, page_size=PAGE_SIZE, sorting="END_DATE_ASC")
        except Exception as exc:
            print(f"  [WARN] {label} pagina {page}: {exc}", file=sys.stderr)
            break

        lots_data = props["lotsData"]
        results = lots_data["results"]
        total = lots_data["totalSize"]

        reached_cutoff = False
        for raw in results:
            if raw["endDate"] > cutoff_ts:
                reached_cutoff = True
                break
            lots.append(
                Lot(
                    id=raw["displayId"],
                    title=raw["title"],
                    category=label,
                    city=raw["location"]["city"],
                    country_code=raw["location"]["countryCode"],
                    current_bid_eur=raw["currentBidAmount"]["cents"] / 100,
                    end_date=raw["endDate"],
                    url=f"https://www.troostwijkauctions.com/l/{raw['urlSlug']}",
                )
            )

        print(f"  {label}: pagina {page} -- {len(lots)} binnen venster (totaal categorie: {total})")

        if reached_cutoff or not results or page * PAGE_SIZE >= total:
            break
        if page >= MAX_PAGES_PER_CATEGORY:
            print(f"  [LIMIET] {label}: gestopt na {MAX_PAGES_PER_CATEGORY} pagina's (categorie heeft meer binnen het venster)")
            break
        page += 1
        time.sleep(DELAY_SEC)

    return lots


def write_csv(path: Path, lots: list) -> None:
    is_new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(
                ["categorie", "titel", "stad", "land", "bod_eur", "allin_eur", "sluit_utc", "url"]
            )
        for lot in lots:
            closes = datetime.fromtimestamp(lot.end_date, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            writer.writerow(
                [
                    lot.category,
                    lot.title,
                    lot.city,
                    lot.country_code.upper(),
                    f"{lot.current_bid_eur:.2f}",
                    f"{lot.current_bid_eur * 1.19:.2f}",
                    closes,
                    lot.url,
                ]
            )


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    csv_path = OUTPUT_DIR / f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    now = datetime.now(timezone.utc).timestamp()
    cutoff_ts = now + CLOSING_WINDOW_DAYS * 86400

    categories = fetch_menu_categories()
    relevant = [c for c in categories if c["title"] not in SKIP_CATEGORIES]

    total_scanned = 0
    total_passed = 0

    for i, cat in enumerate(relevant, 1):
        label = cat["title"]
        path = cat["slug"].split("?")[0]
        print(f"\n=== [{i}/{len(relevant)}] {label} ===")

        lots = scan_category(label, path, cutoff_ts)
        total_scanned += len(lots)

        passed = screen_lots(lots, max_km=100.0, extra_cost_pct=0.19, max_total_eur=500.0)
        total_passed += len(passed)
        write_csv(csv_path, passed)

        print(f"  -> {len(passed)}/{len(lots)} binnen budget+afstand")
        time.sleep(DELAY_SEC)

    print(f"\n\n=== KLAAR ===")
    print(f"Venster: kavels die sluiten tussen nu en {CLOSING_WINDOW_DAYS} dagen")
    print(f"Totaal gescand binnen venster: {total_scanned} kavels over {len(relevant)} categorieen")
    print(f"Totaal binnen budget (<=EUR500 all-in) + afstand (<=100km Bree): {total_passed}")
    print(f"Resultaten: {csv_path}")


if __name__ == "__main__":
    main()
