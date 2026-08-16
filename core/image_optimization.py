"""Downscale and re-encode uploaded images before they are written to storage.

The media library is full of straight-off-the-camera files -- the largest hut
photo is 15.3 MB at 5680x2988 -- because ImageField stores whatever the browser
sent. Nothing on either the site or the dashboard renders anything close to that
size, so every one of those bytes is paid for on upload, on storage, and again
on the "download original" path.

This hooks pre_save globally, so it covers every ImageField on every model,
including ones added later. Delivery-time resizing is handled separately by the
Supabase render endpoint; this is about not hoarding the originals.
"""

import io
import logging
import os

from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# iPhone uploads arrive as HEIC; without this Pillow cannot open them at all.
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:  # pragma: no cover - optional dependency
    pass

# Generous enough to stay a usable "original" (still larger than any 1600px
# layout asks for) while cutting a 12-megapixel camera file down by ~20x.
MAX_EDGE = 2560
JPEG_QUALITY = 85
WEBP_QUALITY = 85

# Anything smaller than this is already cheap; re-encoding risks making it
# bigger and costs CPU on every save.
MIN_BYTES = 256 * 1024

# Animated or vector content must be passed through untouched.
SKIP_EXTENSIONS = {".gif", ".svg", ".ico"}


def _target_format(pillow_format, has_alpha):
    """Pick the output format, keeping the file extension meaningful."""
    fmt = (pillow_format or "").upper()
    if fmt == "PNG":
        # Keep PNG only when the alpha channel is actually doing something.
        return "PNG" if has_alpha else "JPEG"
    if fmt == "WEBP":
        return "WEBP"
    # HEIC and anything else photographic becomes a JPEG.
    return "JPEG"


def _has_alpha(image):
    if image.mode not in ("RGBA", "LA", "P"):
        return False
    alpha = image.convert("RGBA").getchannel("A")
    return alpha.getextrema()[0] < 255


EXTENSION_FOR_FORMAT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def optimize_image_bytes(data, name, max_edge=MAX_EDGE, preserve_format=False):
    """Downscale and re-encode raw image bytes.

    Returns (new_bytes, extension) or None when the image should be left alone
    -- because it is not an image, is already small, or would not get smaller.

    preserve_format keeps the original codec so the file extension (and
    therefore the URL) does not change. That matters when rewriting objects
    that are already published under a known key.
    """
    if os.path.splitext(name)[1].lower() in SKIP_EXTENSIONS:
        return None

    size = len(data)
    if size < MIN_BYTES:
        return None

    try:
        source = Image.open(io.BytesIO(data))
        source.load()
    except Exception as exc:
        logger.warning("Skipping image optimization for %s: %s", name, exc)
        return None

    original_format = (source.format or "").upper()
    # Honour the camera's EXIF orientation before the metadata is dropped,
    # otherwise portrait shots come back rotated.
    source = ImageOps.exif_transpose(source)

    alpha = _has_alpha(source)
    if preserve_format:
        if original_format not in EXTENSION_FOR_FORMAT:
            return None
        out_format = original_format
    else:
        out_format = _target_format(original_format, alpha)

    width, height = source.size
    scale = min(max_edge / max(width, height), 1.0)
    if scale < 1.0:
        source = source.resize(
            (max(1, round(width * scale)), max(1, round(height * scale))),
            Image.LANCZOS,
        )

    buffer = io.BytesIO()
    if out_format == "JPEG":
        source.convert("RGB").save(
            buffer, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True
        )
    elif out_format == "PNG":
        # A palette-mode PNG must keep its palette or it balloons in size.
        source.convert("RGBA" if alpha else "RGB").save(
            buffer, "PNG", optimize=True
        )
    else:
        source.save(buffer, "WEBP", quality=WEBP_QUALITY, method=6)

    # A re-encode that saves nothing is not worth the quality loss.
    if buffer.tell() >= size:
        return None

    return buffer.getvalue(), EXTENSION_FOR_FORMAT[out_format]


def compress_upload(field_file):
    """Return a ContentFile with the optimized bytes, or None to leave as-is."""
    name = getattr(field_file, "name", "") or ""
    try:
        field_file.seek(0)
        data = field_file.read()
    except Exception:
        return None

    result = optimize_image_bytes(data, name)
    if result is None:
        return None

    new_bytes, extension = result
    stem = os.path.splitext(os.path.basename(name))[0]
    logger.info(
        "Optimized %s: %.1f KB -> %.1f KB", name, len(data) / 1024,
        len(new_bytes) / 1024,
    )
    return ContentFile(new_bytes, name=f"{stem}{extension}")


@receiver(pre_save)
def optimize_image_fields(sender, instance, **kwargs):
    """Compress any freshly uploaded ImageField before it is written out."""
    # Django's own tables (sessions, migrations, admin log) never carry images.
    if sender._meta.app_label in {"admin", "auth", "contenttypes", "sessions"}:
        return

    for field in instance._meta.fields:
        if not isinstance(field, models.ImageField):
            continue

        field_file = getattr(instance, field.name, None)
        # _committed is False only for a newly assigned upload; without this
        # guard every plain .save() would re-compress an already stored file.
        if not field_file or getattr(field_file, "_committed", True):
            continue

        try:
            optimized = compress_upload(field_file)
        except Exception as exc:
            logger.warning("Image optimization failed for %s: %s", field.name, exc)
            continue

        if optimized is not None:
            setattr(instance, field.name, optimized)
