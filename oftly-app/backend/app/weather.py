"""Optional destination weather via Open-Meteo (no API key).

Called only when the user has switched weather on. Only the place name is sent to Open-Meteo. Fixed hosts, no redirects,
short timeout, size cap. Never invents data: on any failure it returns {"available": False, "reason": ...} and the
app carries on without weather. Humidity for future days is averaged from hourly values; if the API omits a value the
field is None and the UI says "not available" rather than guessing."""
import re
import time
from datetime import date, timedelta

import httpx

GEO = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST = "https://api.open-meteo.com/v1/forecast"
MAX_DAY = 6
PLACE_OK = re.compile(r"^[^\x00-\x1f<>{}\[\]\\|^`]{1,80}$")
BANDS = ["winter", "autumn", "spring", "summer"]                 # coldest -> hottest (matches item season tags)
BAND_LABEL = {"winter": "cold", "autumn": "cool", "spring": "mild", "summer": "hot"}
_cache: dict = {}


def band(temp_c: float) -> str:
    return "winter" if temp_c <= 10 else "autumn" if temp_c <= 17 else "spring" if temp_c <= 25 else "summer"


def _get(url, params):
    r = httpx.get(url, params=params, timeout=6.0, follow_redirects=False)
    r.raise_for_status()
    if len(r.content) > 400_000:
        raise ValueError("response too large")
    return r.json()


def _first(seq, i=0):
    try:
        return seq[i]
    except (TypeError, IndexError):
        return None


def lookup(place: str, day: int = 0) -> dict:
    place = (place or "").strip()
    if not place:
        return {"available": False, "reason": "No place set."}
    if not PLACE_OK.match(place):
        return {"available": False, "reason": "That place name has characters OFTLY can't send."}
    if not 0 <= day <= MAX_DAY:
        return {"available": False, "reason": f"Forecasts cover today and the next {MAX_DAY} days."}
    key = (place.lower(), day)
    hit = _cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    try:
        res = _first((_get(GEO, {"name": place, "count": 1, "language": "en", "format": "json"}).get("results")))
        if not res:
            out, ttl = {"available": False, "reason": "Place not found."}, 300
        else:
            f = _get(FORECAST, {
                "latitude": res["latitude"], "longitude": res["longitude"], "forecast_days": day + 1, "timezone": "auto",
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,is_day",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
                "hourly": "relative_humidity_2m"})
            cur, daily = f.get("current") or {}, f.get("daily") or {}
            tmax, tmin = _first(daily.get("temperature_2m_max"), day), _first(daily.get("temperature_2m_min"), day)
            hum_h = [h for h in ((f.get("hourly") or {}).get("relative_humidity_2m") or [])[day * 24:(day + 1) * 24] if h is not None]
            if day == 0:
                temp, hum, wind = cur.get("temperature_2m"), cur.get("relative_humidity_2m"), cur.get("wind_speed_10m")
            else:
                temp = round((tmax + tmin) / 2, 1) if tmax is not None and tmin is not None else None
                hum = round(sum(hum_h) / len(hum_h)) if hum_h else None
                wind = _first(daily.get("wind_speed_10m_max"), day)
            if temp is None:
                raise ValueError("no temperature in response")
            out, ttl = {"available": True, "city": res.get("name"), "country": res.get("country"), "day": day,
                        "date": (date.today() + timedelta(days=day)).isoformat(), "temp_c": temp, "temp_min": tmin, "temp_max": tmax,
                        "humidity": hum, "wind_kph": wind, "rain_chance": _first(daily.get("precipitation_probability_max"), day),
                        "band": band(temp), "is_day": bool(cur.get("is_day")) if day == 0 else None,
                        "as_of": cur.get("time") if day == 0 else None, "source": "Open-Meteo"}, 1800
    except Exception:
        out, ttl = {"available": False, "reason": "Weather service unreachable."}, 300
    _cache[key] = (time.time() + ttl, out)
    return out
