"""Render the map picture that rides along with a booking confirmation.

Run this once, and again whenever a hut moves:

    python manage.py build_map_preview

Tiles come from OpenStreetMap. This is deliberately a build step rather than
something the mailer does: it keeps a third party's uptime out of the path of
an email that follows a payment, and it means the tile servers see a handful
of requests when somebody runs this, not a burst per booking. OpenStreetMap's
licence requires the credit that is drawn into the corner of the image.
"""
import io
import math
import os
import time
import urllib.request

from django.core.management.base import BaseCommand

from products.map_preview import ASSETS, asset_name, asset_path

TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
TILE = 256

# Identifying the caller is required by the tile usage policy.
USER_AGENT = "KenAlReef-booking-emails/1.0 (+https://www.kenluxuryreef.com)"

WIDTH, HEIGHT, ZOOM = 600, 300, 15

BROWN = (107, 44, 28)      # --color-red-clay, the brand's marker colour
INK = (63, 46, 30)


def _deg2num(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    return (lon + 180.0) / 360.0 * n, (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n


class Command(BaseCommand):
    help = "Build the map preview images used by booking confirmation emails."

    def add_arguments(self, parser):
        parser.add_argument("--zoom", type=int, default=ZOOM)
        parser.add_argument("--force", action="store_true",
                            help="Rebuild even if the file already exists.")
        parser.add_argument(
            "--coords", action="append", default=[], metavar="LAT,LNG",
            help="Build for these coordinates instead of reading the huts. "
                 "Repeatable. Useful when running away from the production "
                 "database, whose coordinates are the ones that matter.")

    def handle(self, *args, **options):
        from PIL import Image, ImageDraw
        from products.models import Hut

        os.makedirs(ASSETS, exist_ok=True)
        zoom = options["zoom"]

        # One image per distinct location, not per hut: the huts share a site.
        wanted = {}
        if options["coords"]:
            for raw in options["coords"]:
                lat_s, _, lng_s = raw.partition(",")
                wanted.setdefault((float(lat_s), float(lng_s)), []).append("--coords")
        else:
            for hut in Hut.objects.select_related("location"):
                loc = hut.location
                if not loc or loc.latitude is None or loc.longitude is None:
                    self.stdout.write(f"  {hut.title}: no coordinates, skipped")
                    continue
                wanted.setdefault((float(loc.latitude), float(loc.longitude)), []).append(hut.title)

        if not wanted:
            self.stdout.write(self.style.WARNING("No hut has coordinates; nothing to build."))
            return

        for (lat, lng), titles in wanted.items():
            path = asset_path(lat, lng)
            if os.path.exists(path) and not options["force"]:
                self.stdout.write(f"  {asset_name(lat, lng)} exists, skipped (use --force)")
                continue

            self.stdout.write(f"  building {asset_name(lat, lng)} for {', '.join(titles)} ...")
            x, y = _deg2num(lat, lng, zoom)
            cx, cy = x * TILE, y * TILE
            left, top = cx - WIDTH / 2, cy - HEIGHT / 2

            canvas = Image.new("RGB", (WIDTH, HEIGHT), (238, 232, 220))
            first_x, first_y = int(left // TILE), int(top // TILE)
            last_x, last_y = int((left + WIDTH) // TILE), int((top + HEIGHT) // TILE)

            for tx in range(first_x, last_x + 1):
                for ty in range(first_y, last_y + 1):
                    url = TILE_URL.format(z=zoom, x=tx, y=ty)
                    try:
                        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                        with urllib.request.urlopen(request, timeout=30) as response:
                            tile = Image.open(io.BytesIO(response.read())).convert("RGB")
                    except Exception as exc:  # noqa: BLE001 - one missing tile is not fatal
                        self.stdout.write(self.style.WARNING(f"    tile {tx},{ty} failed: {exc}"))
                        continue
                    canvas.paste(tile, (int(tx * TILE - left), int(ty * TILE - top)))
                    time.sleep(0.12)   # be a polite client

            draw = ImageDraw.Draw(canvas, "RGBA")
            mx, my = WIDTH // 2, HEIGHT // 2
            # A pin: a soft halo, a filled head and a stem down to the point.
            draw.ellipse([mx - 26, my - 26, mx + 26, my + 26], fill=BROWN + (46,))
            draw.polygon([(mx, my + 18), (mx - 8, my + 2), (mx + 8, my + 2)], fill=BROWN)
            draw.ellipse([mx - 11, my - 20, mx + 11, my + 2], fill=BROWN,
                         outline=(255, 255, 255), width=3)
            draw.ellipse([mx - 4, my - 13, mx + 4, my - 5], fill=(255, 255, 255))

            # OpenStreetMap's licence requires this credit to be legible, so it
            # is set in the same face the invoices use rather than PIL's
            # default bitmap font.
            credit = "© OpenStreetMap contributors"
            try:
                from PIL import ImageFont
                font = ImageFont.truetype(
                    os.path.join(os.path.dirname(ASSETS), "Jost-Regular.ttf"), 11)
            except Exception:  # noqa: BLE001 - the credit still has to appear
                font = None
            tw = draw.textlength(credit, font=font)
            draw.rectangle([WIDTH - tw - 14, HEIGHT - 21, WIDTH, HEIGHT],
                           fill=(255, 255, 255, 215))
            draw.text((WIDTH - tw - 7, HEIGHT - 17), credit, fill=INK, font=font)

            # A map is flat colour, so a palette cuts it to roughly a third
            # with no visible loss -- and this rides along with every
            # confirmation email.
            canvas.quantize(colors=192, method=Image.MEDIANCUT).save(
                path, "PNG", optimize=True)
            self.stdout.write(self.style.SUCCESS(
                f"    wrote {path} ({os.path.getsize(path) // 1024} KB)"))

        self.stdout.write("done.")
