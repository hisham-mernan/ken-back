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

    GET  /api/health/storage/            configuration only
    GET  /api/health/storage/?write=1    also performs a round trip
    POST /api/health/storage/            multipart echo: reports what actually
                                         arrived in request.FILES and stores it

The POST form exists because storage was proven working while dashboard
uploads still did nothing -- so the question became whether the file reaches
Django at all through Vercel's WSGI bridge.
"""

import io
import os
import traceback
import urllib.request

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

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


def _multipart_echo(request):
    """Report exactly what arrived, then store it the way a real upload would."""
    result = {
        "method": request.method,
        "content_type": request.META.get("CONTENT_TYPE"),
        "content_length": request.META.get("CONTENT_LENGTH"),
        "post_keys": list(request.POST.keys()),
        "files_keys": list(request.FILES.keys()),
        "files": [
            {
                "field": field,
                "name": f.name,
                "size": f.size,
                "content_type": f.content_type,
            }
            for field in request.FILES
            for f in request.FILES.getlist(field)
        ],
    }

    if not request.FILES:
        result["result"] = "NO FILES RECEIVED"
        result["note"] = (
            "Django parsed the request but request.FILES is empty -- the file "
            "did not survive the trip, or was never attached."
        )
        return result

    field = next(iter(request.FILES))
    upload = request.FILES[field]
    saved_name = None
    try:
        # Same path a model ImageField takes, so the pre_save optimizer runs
        # against the same bytes.
        saved_name = default_storage.save(
            f"uploads/_diagnostic/{upload.name}", upload
        )
        result["saved_as"] = saved_name
        result["url"] = default_storage.url(saved_name)
        try:
            req = urllib.request.Request(
                result["url"], headers={"User-Agent": "storage-check/1.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
            result["public_fetch"] = {
                "status": resp.status,
                "bytes": len(body),
                "content_type": resp.headers.get("Content-Type"),
            }
        except Exception as exc:
            result["public_fetch"] = {"error": f"{type(exc).__name__}: {exc}"}
        result["result"] = "UPLOAD OK"
    except Exception as exc:
        result["result"] = "UPLOAD FAILED"
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc().splitlines()[-6:]
    finally:
        # Keep it only when explicitly asked, so the bucket stays clean.
        if saved_name and request.GET.get("keep") != "1":
            try:
                default_storage.delete(saved_name)
                result["cleaned_up"] = True
            except Exception as exc:
                result["cleaned_up"] = f"failed: {exc}"
        elif saved_name:
            result["cleaned_up"] = False

    return result


def _hut_update_probe(request, hut_id):
    """Run an uploaded file through the exact serializer the dashboard uses.

    The generic write test proved storage works, so this narrows it to the real
    update path: HutAdminDetailsDashboardSerializer -> Hut.main_image -> storage.
    The original value is restored and the new object deleted before returning,
    so the record is left exactly as it was found.
    """
    from products.models import Hut
    from products.serializers import HutAdminDetailsDashboardSerializer

    steps = {"hut_id": hut_id}
    if not request.FILES:
        steps["result"] = "NO FILE POSTED"
        return steps

    try:
        hut = Hut.objects.get(pk=hut_id)
    except Hut.DoesNotExist:
        steps["result"] = f"hut {hut_id} not found"
        return steps

    original_name = hut.main_image.name if hut.main_image else None
    steps["original_main_image"] = original_name

    upload = request.FILES[next(iter(request.FILES))]
    steps["uploaded"] = {"name": upload.name, "size": upload.size}

    new_name = None
    try:
        serializer = HutAdminDetailsDashboardSerializer(
            hut, data={"main_image": upload}, partial=True
        )
        steps["is_valid"] = serializer.is_valid()
        if not steps["is_valid"]:
            steps["errors"] = serializer.errors
            steps["result"] = "SERIALIZER REJECTED THE FILE"
            return steps

        serializer.save()
        hut.refresh_from_db()
        new_name = hut.main_image.name if hut.main_image else None
        steps["new_main_image"] = new_name
        steps["changed"] = new_name != original_name

        if new_name:
            url = default_storage.url(new_name)
            steps["new_url"] = url
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "storage-check/1.0"}
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    body = resp.read()
                steps["public_fetch"] = {
                    "status": resp.status,
                    "bytes": len(body),
                    "content_type": resp.headers.get("Content-Type"),
                }
            except Exception as exc:
                steps["public_fetch"] = {"error": f"{type(exc).__name__}: {exc}"}

        steps["result"] = "UPDATE OK" if steps.get("changed") else "NO CHANGE"
    except Exception as exc:
        steps["result"] = "UPDATE FAILED"
        steps["error"] = f"{type(exc).__name__}: {exc}"
        steps["traceback"] = traceback.format_exc().splitlines()[-6:]
    finally:
        # Put the record back exactly as it was, and remove the new object.
        try:
            if new_name and new_name != original_name:
                Hut.objects.filter(pk=hut_id).update(main_image=original_name)
                steps["restored_to"] = original_name
                if request.GET.get("keep") != "1":
                    default_storage.delete(new_name)
                    steps["deleted_new_object"] = new_name
        except Exception as exc:
            steps["restore_error"] = f"{type(exc).__name__}: {exc}"

    return steps


@csrf_exempt
def storage_check(request):
    if request.method == "POST":
        hut_id = request.GET.get("hut")
        if hut_id:
            return JsonResponse(
                _hut_update_probe(request, hut_id), json_dumps_params={"indent": 2}
            )
        return JsonResponse(
            _multipart_echo(request), json_dumps_params={"indent": 2}
        )

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
