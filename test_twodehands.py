"""Live test van de 2dehands-prijsschatting tegen echte, diverse kaveltitels uit de scan-CSV."""

from twodehands import estimate_resale_value

TEST_TITLES = [
    "EP - EST 3,0 meter Stapelaar - ingebouwde lader - 1500 kg - 2026",
    "Magazijnstelling",
    "Klassieke Zeilboot - 6 meter",
    "Festo PP Ketting freesmachine",
    "AMANDO - IDENTITY - Heren - After Shave Spray (85x)",
    "Yamaha Golfkar",
    "Life Fitness 95 C Home Trainer",
    "2017 Jungheinrich ERE225 Orderpicker (61025-220)",
    "Zoll AED plus",
    "Steigerplank 3000x195x28mm (92x)",
]

for title in TEST_TITLES:
    print(f"\n{'=' * 90}\nKAVEL: {title}")
    result = estimate_resale_value(title)
    if result is None:
        print("  GEEN bruikbare 2dehands-resultaten gevonden (zelfs niet met generieke term)")
        continue
    print(f"  zoekterm gebruikt: '{result['query_used']}'  (n={result['n']})")
    print(f"  mediaanprijs: EUR {result['median_eur']:.2f}   gemiddelde: EUR {result['mean_eur']:.2f}")
    print("  voorbeeldlistings:")
    for listing in result["listings"][:4]:
        print(f"    EUR {listing.price_eur:>7.2f}  [{listing.price_type:<10}]  {listing.title[:55]}")
