# menu/utils.py
import requests
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def get_weather(lat, lon):
    """
    Calls Open-Meteo and maps current conditions to one of:
    'any', 'hot', 'cold', 'rain', 'clear'
    Returns: (condition, {"temperature": t or None, "precipitation": p or None, "weather_code": code or None})
    """
    try:
        # Check cache first (15-minute cache)
        cache_key = f"weather_{lat:.4f}_{lon:.4f}"
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f'Weather cache hit for {lat:.4f}, {lon:.4f}')
            return cached
        
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}&current=temperature_2m,precipitation,weather_code"
        )
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and data.get("error"):
            logger.warning(f'Weather API error for {lat:.4f}, {lon:.4f}: {data.get("error")}')
            return "any", {"temperature": None, "precipitation": None, "weather_code": None}

        cur = data.get("current", {}) or {}
        # sensible defaults if missing
        t = cur.get("temperature_2m")
        p = cur.get("precipitation")
        t = float(t) if t is not None else None
        p = float(p) if p is not None else None

        if p is not None and p >= 0.5:
            cond = "rain"
        elif t is not None and t >= 32:
            cond = "hot"
        elif t is not None and t <= 18:
            cond = "cold"
        elif t is None and p is None:
            cond = "any"   # API fallback → show all active items
        else:
            cond = "clear"

        result = (cond, {"temperature": t, "precipitation": p, "weather_code": cur.get("weather_code")})
        # Cache for 15 minutes (900 seconds)
        cache.set(cache_key, result, 900)
        logger.info(f'Weather fetched for {lat:.4f}, {lon:.4f}: {cond}, {t}°C')
        return result
    except Exception as e:
        logger.error(f'Weather API error for {lat:.4f}, {lon:.4f}: {e}', exc_info=True)
        return "any", {"temperature": None, "precipitation": None, "weather_code": None}
