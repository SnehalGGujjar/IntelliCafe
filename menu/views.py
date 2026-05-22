from django.shortcuts import render
from django.conf import settings
from django.db.models import Q
from django.db.utils import OperationalError, ProgrammingError

from core.models import SiteSetting, Location
from .models import Item, MenuRule
from .utils import get_weather


def today_menu(request):
    """Show today's menu filtered using DB default location."""
    try:
        site = SiteSetting.get_solo()
        lat, lon = site.default_lat, site.default_lon

        # Try matching the nearest Location by coordinates
        loc = (
            Location.objects.filter(lat=lat, lon=lon, is_active=True).first()
            or Location.objects.filter(is_active=True).first()
        )
        location_name = loc.name if loc else "Default Location"
        label = f"{location_name} ({lat:.4f}, {lon:.4f})"
    except (OperationalError, ProgrammingError):
        lat = getattr(settings, "WEATHER_DEFAULT_LAT", 12.9716)
        lon = getattr(settings, "WEATHER_DEFAULT_LON", 77.5946)
        location_name = "System Default"
        label = f"{location_name} ({lat:.4f}, {lon:.4f})"

    # Override with session-based location if set by GPS
    session_lat = request.session.get("geo_lat")
    session_lon = request.session.get("geo_lon")
    session_label = request.session.get("geo_label")
    if session_lat is not None and session_lon is not None:
        lat, lon = float(session_lat), float(session_lon)
        location_name = session_label or "Your Location"
        label = session_label or f"GPS ({lat:.4f}, {lon:.4f})"

    condition, weather = get_weather(lat, lon)

    # Filter menu items by condition
    items_qs = Item.objects.filter(is_active=True)
    if condition == "any":
        filtered = list(items_qs)
    else:
        allowed_ids = set(MenuRule.objects.filter(condition__in=[condition, "any"])
                          .values_list("item_id", flat=True))
        filtered = [i for i in items_qs if (not i.rules.exists()) or (i.id in allowed_ids)]

    return render(request, "menu/today.html", {
        "items": filtered,
        "condition": condition,
        "weather": weather,
        "lat": lat,
        "lon": lon,
        "location_label": label,
        "location_name": location_name,
    })
