"""Live steekproef: STAP 1 (scraper) + STAP 2 (filters) samen, over alle hoofdcategorieen,
gesorteerd op laagste huidige bod, binnen 100km van Bree en onder EUR 500 all-in."""

import sys

from filters import screen_lots
from scraper import fetch_category_page, fetch_menu_categories

RADIUS = "Bree,51.14109,5.59762,100,BE"
SKIP_CATEGORIES = {"Vastgoed"}  # onroerend goed is niet herverkoopbaar als kavel-item
PAGES_PER_CATEGORY = 1  # 1 pagina (48 kavels, PRICE_ASC) per categorie = snelle steekproef


def main():
    categories = fetch_menu_categories()
    all_lots = []

    for cat in categories:
        label = cat["title"]
        if label in SKIP_CATEGORIES:
            continue
        path = cat["slug"].split("?")[0]

        for page in range(1, PAGES_PER_CATEGORY + 1):
            try:
                props = fetch_category_page(path, RADIUS, page, sorting="PRICE_ASC")
            except Exception as exc:
                print(f"  [WARN] {label} pagina {page}: {exc}", file=sys.stderr)
                continue

            results = props["lotsData"]["results"]
            total = props["lotsData"]["totalSize"]
            print(f"{label}: {total} kavels binnen 100km van Bree, {len(results)} opgehaald (pagina {page})")

            for raw in results:
                from filters import Lot

                all_lots.append(
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

    print(f"\nTotaal opgehaald: {len(all_lots)} kavels. Filteren op afstand + budget...\n")

    passed = screen_lots(all_lots, max_km=100.0, extra_cost_pct=0.19, max_total_eur=500.0)
    passed.sort(key=lambda l: l.current_bid_eur)

    print(f"Kavels die BEIDE filters doorstaan ({len(passed)}):\n")
    print(f"{'Categorie':<22} {'Titel':<55} {'Stad':<18} {'Bod':>8} {'All-in':>8}")
    print("-" * 115)
    for lot in passed:
        total_cost = lot.current_bid_eur * 1.19
        print(
            f"{lot.category[:21]:<22} {lot.title[:54]:<55} {lot.city[:17]:<18} "
            f"{lot.current_bid_eur:>7.0f} {total_cost:>8.0f}"
        )
        print(f"   -> {lot.url}")


if __name__ == "__main__":
    main()
