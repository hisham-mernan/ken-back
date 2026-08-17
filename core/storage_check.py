"""Temporary diagnostic endpoint for the media storage configuration.

Uploads through the dashboard were reporting success while no object ever
appeared in the bucket, and nothing distinguishable showed up in the browser's
network tab. From outside the deployment there is no way to tell whether the
SUPABASE_S3_* variables actually resolved in the running instance, so this
reports that directly -- and can run a real write/read/delete round trip
through Django's own storage layer.

It deliberately reports NO secret values: only whether each variable is set,
and its length. Remove this module, its URL entry, and its import once the
upload path is confirmed working.

    GET /api/health/storage/            configuration only
    GET /api/health/storage/?write=1    also performs a round trip
"""

import io
import os
import traceback
import urllib.request

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse

PROBE_KEY = "uploads/_diagnostic/storage_check.png"

# A 1x1 PNG -- small enough that the round trip costs nothing.
ONE_PIXEL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000d49444154789c6360000002000100ffff03000006"
    "0005570bd10000000049454e44ae426082"
)


def _present(name):
    value = os.getenv(name)
    return {"set": bool(value), "length": len(value) if value else 0}


def storage_check(request):
    info = {
        "use_supabase_storage": getattr(settings, "USE_SUPABASE_STORAGE", False),
        "storage_backend": settings.STORAGES["default"]["BACKEND"],
        "media_url": settings.MEDIA_URL,
        "media_root": str(settings.MEDIA_ROOT),
        "aws_s3_custom_domain": getattr(settings, "AWS_S3_CUSTOM_DOMAIN", None),
        "aws_s3_endpoint_url": getattr(settings, "AWS_S3_ENDPOINT_URL", None),
        "bucket": getattr(settings, "AWS_STORAGE_BUCKET_NAME", None),
        "region": getattr(settings, "AWS_S3_REGION_NAME", None),
        "env": {
            name: _present(name)
            for name in (
                "SUPABASE_S3_ENDPOINT",
                "SUPABASE_S3_REGION",
                "SUPABASE_S3_ACCESS_KEY_ID",
                "SUPABASE_S3_SECRET_ACCESS_KEY",
                "SUPABASE_BUCKET",
                "MEDIA_URL",
                "VERCEL",
                "DATABASE_URL",
            )
        },
    }

    if request.GET.get("write") != "1":
        info["write_test"] = "skipped (add ?write=1 to run it)"
        return JsonResponse(info, json_dumps_params={"indent": 2})

    steps = {}
    saved_name = None
    try:
        saved_name = default_storage.save(PROBE_KEY, ContentFile(ONE_PIXEL_PNG))
        steps["saved_as"] = saved_name
        steps["url"] = default_storage.url(saved_name)
        steps["exists_per_storage"] = default_storage.exists(saved_name)

        try:
            req = urllib.request.Request(
                steps["url"], headers={"User-Agent": "storage-check/1.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
            steps["public_fetch"] = {
                "status": resp.status,
                "bytes": len(body),
                "content_type": resp.headers.get("Content-Type"),
                "matches_written_bytes": body == ONE_PIXEL_PNG,
            }
        except Exception as exc:
            steps["public_fetch"] = {"error": f"{type(exc).__name__}: {exc}"}

        steps["result"] = "WRITE OK"
    except Exception as exc:
        steps["result"] = "WRITE FAILED"
        steps["error"] = f"{type(exc).__name__}: {exc}"
        steps["traceback"] = traceback.format_exc().splitlines()[-6:]
    finally:
        if saved_name:
            try:
                default_storage.delete(saved_name)
                steps["cleaned_up"] = True
            except Exception as exc:
                steps["cleaned_up"] = f"failed: {exc}"

    info["write_test"] = steps
    return JsonResponse(info, json_dumps_params={"indent": 2})
