"""Test server: the real OFTLY app, but Open-Meteo is replaced by deterministic fake data so browser tests are offline and repeatable.
Usage (from repo root): OFTLY_DATA=/tmp/oftly-e2e OFTLY_PORT=8011 python tests/frontend/serve_fake_weather.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
import uvicorn
from app import main, weather

def fake(url, params):
    if "geocoding" in url:
        n = params["name"]
        if n.lower() == "atlantis":
            return {}
        return {"results": [{"name": n.title(), "country": "Testland", "latitude": 1, "longitude": 2}]}
    cold = params["latitude"] == 1 and True
    n = params["forecast_days"]
    t = 3.0 if cold else 24.0
    return {"current": {"temperature_2m": t, "relative_humidity_2m": 82, "wind_speed_10m": 34, "is_day": 1, "time": "2026-10-23T12:00"},
            "daily": {"temperature_2m_max": [t + 2] * n, "temperature_2m_min": [t - 2] * n, "precipitation_probability_max": [70] * n, "wind_speed_10m_max": [40] * n},
            "hourly": {"relative_humidity_2m": [75] * 24 * n}}

weather._get = fake
uvicorn.run(main.app, host="127.0.0.1", port=int(os.environ.get("OFTLY_PORT", "8011")), log_level="warning")
