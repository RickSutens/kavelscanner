"""STAP 4: combineert de gefilterde kavellijst (CSV van full_scan.py) met 2dehands-prijzen
tot een marge-score, en schrijft een shortlist gesorteerd op hoogste marge.

Om de runtime behapbaar te houden voor deze eerste volledige testrun nemen we per categorie de
TOP_PER_CATEGORY duurste kavels die nog binnen budget vallen (die hebben het meeste marge-
potentieel) i.p.v. alle ~10.000 kandidaten -- dat laatste zou met beleefde snelheidslimieten
uren duren. Aanpasbaar via TOP_PER_CATEGORY / MIN_ALLIN_EUR hieronder."""

import csv
import sys
import time
from collections import defaultdict
from pathlib import Path

from filters import Lot, is_excluded_by_keyword
from margin import compute_margin
from scraper import fetch_lot_detail
from twodehands import estimate_resale_value

TOP_PER_CATEGORY = 8
MIN_ALLIN_EUR = 20.0  # kavels goedkoper dan dit zijn zelden de moeite van het opzoeken waard
DELAY_SEC = 1.0

OUTPUT_DIR = Path(__file__).parent / "output"


def load_candidates(csv_path: Path) -> list:
    by_category = defaultdict(list)
    seen_titles = set()
    with csv_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            allin = float(row["allin_eur"])
            if allin < MIN_ALLIN_EUR:
                continue
            if is_excluded_by_keyword(row["titel"]):
                continue
            # identieke titel+stad+bod is zo goed als zeker een duplicaat-kavel (zelfde partij,
            # apart lotnummer) -- niet nog eens dezelfde 2dehands-opzoeking herhalen.
            dedup_key = (row["titel"], row["stad"], row["bod_eur"])
            if dedup_key in seen_titles:
                continue
            seen_titles.add(dedup_key)
            by_category[row["categorie"]].append(row)

    selected = []
    for cat, rows in by_category.items():
        rows.sort(key=lambda r: float(r["allin_eur"]), reverse=True)
        selected.extend(rows[:TOP_PER_CATEGORY])
    return selected


def main():
    if len(sys.argv) < 2:
        print("Gebruik: python3 run_pipeline.py output/scan_XXXXXXXX_XXXXXX.csv")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    candidates = load_candidates(csv_path)
    print(f"{len(candidates)} kandidaten geselecteerd (top {TOP_PER_CATEGORY}/categorie, allin >= EUR{MIN_ALLIN_EUR})\n")

    results = []
    for i, row in enumerate(candidates, 1):
        title = row["titel"]
        print(f"[{i}/{len(candidates)}] {row['categorie'][:25]:<25} {title[:50]}", end=" ... ")

        try:
            detail = fetch_lot_detail(row["url"])
            quantity = detail["lot"]["quantity"]
        except Exception as exc:
            print(f"FOUT (quantity): {exc}", file=sys.stderr)
            continue
        time.sleep(DELAY_SEC)

        try:
            estimate = estimate_resale_value(title)
        except Exception as exc:
            print(f"FOUT (2dehands): {exc}", file=sys.stderr)
            time.sleep(DELAY_SEC)
            continue
        time.sleep(DELAY_SEC)

        if estimate is None:
            print("geen 2dehands-resultaten")
            continue

        lot = Lot(
            id=row["url"].rsplit("-", 1)[-1],
            title=title,
            category=row["categorie"],
            city=row["stad"],
            country_code=row["land"].lower(),
            current_bid_eur=float(row["bod_eur"]),
            end_date=0,
            url=row["url"],
            quantity=quantity,
        )
        sample_listings = [
            f"EUR{l.price_eur:.0f} {l.title}" for l in estimate["listings"][:3]
        ]
        result = compute_margin(
            lot,
            quantity=quantity,
            resale_median_eur=estimate["median_eur"],
            resale_n=estimate["n"],
            resale_query=estimate["query_used"],
            sample_listings=sample_listings,
        )
        results.append(result)
        flag = "" if result.confidence == "hoog" else f"  [LAAG: {result.confidence_reason}]"
        print(f"marge EUR{result.margin_eur:.0f} (x{quantity}, query='{estimate['query_used']}', n={estimate['n']}){flag}")

    results.sort(key=lambda r: r.margin_eur, reverse=True)

    out_path = OUTPUT_DIR / f"margins_{csv_path.stem}.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "categorie", "titel", "stad", "land", "aantal", "bod_eur", "allin_eur",
                "2dehands_query", "2dehands_mediaan_eur", "2dehands_n", "verkoopwaarde_eur",
                "marge_eur", "roi_multiple", "betrouwbaarheid", "reden_laag", "voorbeeldlistings", "url",
            ]
        )
        for r in results:
            writer.writerow(
                [
                    r.lot.category, r.lot.title, r.lot.city, r.lot.country_code.upper(), r.quantity,
                    f"{r.lot.current_bid_eur:.2f}", f"{r.allin_cost_eur:.2f}", r.resale_query,
                    f"{r.resale_median_eur:.2f}", r.resale_n, f"{r.total_resale_value_eur:.2f}",
                    f"{r.margin_eur:.2f}", f"{r.roi_multiple:.2f}", r.confidence, r.confidence_reason,
                    " | ".join(r.sample_listings), r.lot.url,
                ]
            )

    confident = [r for r in results if r.confidence == "hoog"]
    low_conf = [r for r in results if r.confidence == "laag"]

    print(f"\n=== TOP 20 op marge (betrouwbaarheid: hoog) ===")
    for r in confident[:20]:
        print(
            f"EUR{r.margin_eur:>7.0f} marge (x{r.roi_multiple:.1f})  [{r.lot.category[:20]}] {r.lot.title[:45]:<45} "
            f"bod EUR{r.lot.current_bid_eur:.0f} x{r.quantity} -> EUR{r.total_resale_value_eur:.0f} "
            f"(query='{r.resale_query}', n={r.resale_n})"
        )
        print(f"    {r.lot.url}")

    print(f"\n({len(low_conf)} resultaten met LAGE betrouwbaarheid weggelaten uit de top -- staan wel in de CSV)")
    print(f"Volledige resultaten: {out_path}")


if __name__ == "__main__":
    main()
