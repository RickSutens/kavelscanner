"""Geocoding van stad+land naar (lat, lon) via OpenStreetMap Nominatim, met lokale disk-cache."""

import json
import time
import urllib.request
from pathlib import Path
from typing import Tuple
from urllib.parse import quote

CACHE_PATH = Path(__file__).parent / "geocode_cache.json"
USER_AGENT = "kavelscanner-personal-tool/0.1"
MIN_INTERVAL_SEC = 1.1  # Nominatim usage policy: max 1 request/seconde

_last_request_time = 0.0


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False))


def geocode(city: str, country_code: str) -> Tuple[float, float]:
    """Geeft (lat, lon) voor een stad+landcode. Gecached op disk zodat elke stad maar 1x wordt opgezocht."""
    global _last_request_time

    key = f"{city.strip().lower()}|{country_code.strip().lower()}"
    cache = _load_cache()
    if key in cache:
        return tuple(cache[key])

    elapsed = time.time() - _last_request_time
    if elapsed < MIN_INTERVAL_SEC:
        time.sleep(MIN_INTERVAL_SEC - elapsed)

    url = (
        "https://nominatim.openstreetmap.org/search?"
        f"city={quote(city)}&country={quote(country_code)}&format=json&limit=1"
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    _last_request_time = time.time()

    if not data:
        raise ValueError(f"Kon '{city}, {country_code}' niet geocoderen")

    lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
    cache[key] = [lat, lon]
    _save_cache(cache)
    return lat, lon
