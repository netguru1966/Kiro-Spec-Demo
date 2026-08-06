"""weather.py — fetch current temperature and chance of rain for a US zip code."""

import sys
import re
import argparse
from datetime import datetime, timezone

DEFAULT_ZIP = "10001"  # New York, NY

try:
    import requests
except ImportError:
    print(
        "Error: Required package 'requests' not found. "
        "Run: pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)


def validate_zip(zip_code: str) -> str:
    if not re.fullmatch(r"[0-9]{5}", zip_code):
        print(
            f"Error: Invalid zip code '{zip_code}'. Must be exactly 5 digits.",
            file=sys.stderr,
        )
        sys.exit(1)
    return zip_code


def get_coordinates(zip_code: str) -> tuple:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": zip_code, "count": 1, "language": "en", "format": "json"}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: Failed to reach geocoding service — {e}", file=sys.stderr)
        sys.exit(1)

    results = data.get("results")
    if not results:
        print(f"Error: No location found for zip code {zip_code}", file=sys.stderr)
        sys.exit(1)

    first = results[0]
    try:
        return float(first["latitude"]), float(first["longitude"])
    except (KeyError, TypeError, ValueError) as e:
        print(f"Error: Unexpected geocoding response format — {e}", file=sys.stderr)
        sys.exit(1)


def find_current_hour_index(times: list) -> int:
    current_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    current_str = current_hour.strftime("%Y-%m-%dT%H:00")
    for i, t in enumerate(times):
        if t == current_str:
            return i
    # Fallback: match by hour of day if date differs
    current_h = current_hour.hour
    for i, t in enumerate(times):
        try:
            if datetime.fromisoformat(t).hour == current_h:
                return i
        except ValueError:
            continue
    return 0


def get_weather(lat: float, lon: float) -> tuple:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation_probability",
        "temperature_unit": "fahrenheit",
        "forecast_days": 1,
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: Failed to reach weather service — {e}", file=sys.stderr)
        sys.exit(1)

    try:
        hourly = data["hourly"]
        times = hourly["time"]
        temps = hourly["temperature_2m"]
        rain = hourly["precipitation_probability"]
    except KeyError as e:
        print(f"Error: Unexpected response format — missing field {e}", file=sys.stderr)
        sys.exit(1)

    idx = find_current_hour_index(times)
    return float(temps[idx]), int(rain[idx])


def get_advisory(lat: float, lon: float):
    SEVERITY_ORDER = {"Extreme": 0, "Severe": 1, "Moderate": 2, "Minor": 3, "Unknown": 4}
    url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"
    try:
        response = requests.get(url, headers={"Accept": "application/geo+json"}, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not retrieve weather advisories — {e}")
        return None

    try:
        features = data["features"]
    except (KeyError, TypeError):
        print("Warning: Unexpected advisory response structure.")
        return None

    if not features:
        return None

    def severity_rank(feature):
        sev = feature.get("properties", {}).get("severity", "Unknown")
        return SEVERITY_ORDER.get(sev, 4)

    best = min(features, key=severity_rank)
    props = best.get("properties", {})

    def sanitize(text: str) -> str:
        if text is None:
            return ""
        return "".join(c if 0x20 <= ord(c) <= 0x7E else "?" for c in str(text))

    description = props.get("description") or ""
    return {
        "event": sanitize(props.get("event")),
        "severity": sanitize(props.get("severity")),
        "headline": sanitize(props.get("headline")),
        "description": sanitize(description[:500]),
    }


def print_weather(zip_code: str, temp: float, rain: int, advisory=None) -> None:
    print(f"Location: {zip_code}")
    print(f"Temperature: {temp:.1f}degF")
    print(f"Chance of Rain: {rain}%")
    if advisory is not None:
        print(f"Advisory Event: {advisory['event']}")
        print(f"Advisory Severity: {advisory['severity']}")
        print(f"Advisory Headline: {advisory['headline']}")
        print(f"Advisory Description: {advisory['description']}")
    else:
        print("Advisory: No active advisories")


def main() -> None:
    validate_zip(DEFAULT_ZIP)  # Fail fast if the constant is misconfigured

    parser = argparse.ArgumentParser(
        description="Fetch current temperature and chance of rain for a US zip code."
    )
    parser.add_argument(
        "zip_code",
        nargs="?",
        default=DEFAULT_ZIP,
        help="US zip code (5 digits). Defaults to DEFAULT_ZIP if omitted.",
    )
    args = parser.parse_args()

    zip_code = validate_zip(args.zip_code)
    lat, lon = get_coordinates(zip_code)
    temp, rain = get_weather(lat, lon)
    advisory = get_advisory(lat, lon)
    print_weather(zip_code, temp, rain, advisory)


if __name__ == "__main__":
    main()
