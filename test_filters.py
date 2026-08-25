"""Test van de afstands- en budgetfilter met kavels die echt op Troostwijk stonden
(bouw-en-grondverzet categorie, 25/08/2026), plus twee synthetische goedkope kavels
om te bevestigen dat er ook kavels dóórkomen."""

from filters import Lot, screen_lots, within_budget, within_distance

real_lots = [
    Lot(
        id="A1-48676-2",
        title="1994 Grove RT 630 C Mobiele kraan",
        category="Bouw en grondverzet",
        city="Schoorl",
        country_code="nl",
        opening_bid_eur=5000,
        current_bid_eur=9000,
        end_date=1788252420,
        url="https://www.troostwijkauctions.com/l/1994-grove-rt-630-c-mobiele-kraan-A1-48676-2",
    ),
    Lot(
        id="A1-48766-6",
        title="2019 Volvo EWR150E Banden graafmachine",
        category="Bouw en grondverzet",
        city="Lommel",
        country_code="be",
        opening_bid_eur=15000,
        current_bid_eur=21500,
        end_date=1787664300,
        url="https://www.troostwijkauctions.com/l/2019-volvo-ewr150e-banden-graafmachine-A1-48766-6",
    ),
    Lot(
        id="A1-49137-1",
        title="Spierings SK365 AT3 Mobiele Torenkraan 1999",
        category="Bouw en grondverzet",
        city="Grebocice",
        country_code="pl",
        opening_bid_eur=10000,
        current_bid_eur=15000,
        end_date=1787659320,
        url="https://www.troostwijkauctions.com/l/spierings-sk365-at3-mobiele-torenkraan-1999-A1-49137-1",
    ),
    Lot(
        id="A1-49156-5",
        title="Komptech Jumbo Mobiele trommelzeef",
        category="Bouw en grondverzet",
        city="Hechtel-Eksel",
        country_code="be",
        opening_bid_eur=18000,
        current_bid_eur=26000,
        end_date=1787659500,
        url="https://www.troostwijkauctions.com/l/komptech-jumbo-mobiele-trommelzeef-A1-49156-5",
    ),
    # Synthetisch (lage prijs) om te bevestigen dat goedkope + dichtbij kavels wél doorkomen.
    Lot(
        id="TEST-1",
        title="[TEST] Goedkoop handgereedschap, dichtbij",
        category="Test",
        city="Lommel",
        country_code="be",
        opening_bid_eur=50,
        current_bid_eur=180,
        end_date=1787664300,
        url="https://example.invalid/test-1",
    ),
    Lot(
        id="TEST-2",
        title="[TEST] Goedkoop, maar te ver weg (Schoorl)",
        category="Test",
        city="Schoorl",
        country_code="nl",
        opening_bid_eur=50,
        current_bid_eur=180,
        end_date=1787664300,
        url="https://example.invalid/test-2",
    ),
]

EXPECTED_DISTANCE_OK = {
    "A1-48676-2": False,  # Schoorl, NL -> ver van Bree
    "A1-48766-6": True,   # Lommel, BE -> vlakbij Bree
    "A1-49137-1": False,  # Grebocice, PL -> ver van Bree
    "A1-49156-5": True,   # Hechtel-Eksel, BE -> vlakbij Bree
    "TEST-1": True,
    "TEST-2": False,
}

EXPECTED_BUDGET_OK = {
    "A1-48676-2": False,  # 9000 * 1.19 = 10710 -> ruim boven 500
    "A1-48766-6": False,
    "A1-49137-1": False,
    "A1-49156-5": False,
    "TEST-1": True,  # 180 * 1.19 = 214.20 -> onder 500
    "TEST-2": True,  # budget-check op zich is ok, distance-check filtert 'm eruit
}


def run():
    print(f"{'Kavel':<45} {'Afstand OK':<12} {'Budget OK':<12} {'Verwacht/Actueel'}")
    all_ok = True
    for lot in real_lots:
        dist_ok = within_distance(lot)
        budget_ok = within_budget(lot)
        exp_dist = EXPECTED_DISTANCE_OK[lot.id]
        exp_budget = EXPECTED_BUDGET_OK[lot.id]
        match = (dist_ok == exp_dist) and (budget_ok == exp_budget)
        all_ok &= match
        flag = "OK" if match else "MISMATCH"
        print(f"{lot.title[:44]:<45} {str(dist_ok):<12} {str(budget_ok):<12} {flag}")

    print()
    passed = screen_lots(real_lots)
    print(f"Kavels die BEIDE filters doorstaan ({len(passed)}):")
    for lot in passed:
        total = lot.current_bid_eur * 1.19
        print(f"  - {lot.title} ({lot.city}, {lot.country_code.upper()}) -> all-in ~EUR {total:.2f}")

    print()
    print("ALLE TESTS GESLAAGD" if all_ok else "ER ZIJN MISMATCHES -- controleer hierboven")
    return all_ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if run() else 1)
