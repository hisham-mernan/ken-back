"""The "where to find us" block that goes out with a booking confirmation.

A guest who has just paid needs to know where to turn up, so the confirmation
carries a small map picture and a link that opens the place in Google Maps.

The picture is a file in this repo, not a live request. Two reasons:

* Google's Static Maps API refuses this project's key. The key is restricted
  to the website's own domains, and an email has no referer to offer, so the
  request comes back 403 wherever the guest happens to open it.
* Fetching map tiles while sending would put a network call, and somebody
  else's uptime, in the path of an email that follows a payment that has
  already gone through.

``manage.py build_map_preview`` renders the asset from OpenStreetMap tiles;
sending only reads the file. The image is attached inline, like the booking QR
beside it, so it survives a client that blocks remote images.

Regenerate after moving a hut: the file is keyed by rounded coordinates, so a
hut whose location changes simply stops matching one and the email falls back
to the link on its own rather than showing the wrong place.
"""
import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)

ASSETS = os.path.join(os.path.dirname(__file__), "assets", "maps")

# Enough precision to place a building, few enough digits to stay a stable
# filename across trivial edits to the record.
_PRECISION = 4


def _coords(hut):
    location = getattr(hut, "location", None) if hut else None
    lat = getattr(location, "latitude", None)
    lng = getattr(location, "longitude", None)
    if lat is None or lng is None:
        return None
    try:
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


def asset_name(lat, lng):
    return f"{round(lat, _PRECISION)}_{round(lng, _PRECISION)}.png"


def asset_path(lat, lng):
    return os.path.join(ASSETS, asset_name(lat, lng))


def place_url(hut):
    """Where the map picture and the link should take the guest.

    A configured place link is preferred: it opens the business itself, with
    its name, photos and directions, rather than a bare pin. Without one, the
    hut's own coordinates still give a link that works everywhere and opens
    the maps app on a phone.
    """
    configured = (getattr(settings, "MAP_PLACE_URL", "") or "").strip()
    if configured:
        return configured
    coords = _coords(hut)
    if not coords:
        return ""
    lat, lng = coords
    return f"https://www.google.com/maps/search/?api=1&query={lat}%2C{lng}"


def preview_bytes(hut):
    """PNG bytes for this hut's map picture, or None if it has not been built."""
    coords = _coords(hut)
    if not coords:
        return None
    path = asset_path(*coords)
    if not os.path.exists(path):
        logger.info(
            "No map preview built for %s; the confirmation will carry the "
            "link only. Run: manage.py build_map_preview",
            asset_name(*coords),
        )
        return None
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError as exc:
        logger.warning("Could not read map preview %s: %s", path, exc)
        return None


def email_context(hut):
    """Template variables for the location block.

    ``map_cid`` is only set when there is a picture to attach, so the template
    can show the link on its own rather than a broken image.
    """
    url = place_url(hut)
    if not url:
        return {"map_url": "", "map_cid": "", "map_address": ""}

    location = getattr(hut, "location", None)
    address = ""
    for field in ("address", "address_ar"):
        value = (getattr(location, field, "") or "").strip() if location else ""
        if value:
            address = value
            break

    return {
        "map_url": url,
        "map_cid": "booking_map" if preview_bytes(hut) else "",
        "map_address": address,
    }
