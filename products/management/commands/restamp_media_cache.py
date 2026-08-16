"""Re-stamp Cache-Control on objects already in the Supabase bucket.

The existing uploads are served with `Cache-Control: no-cache`, so browsers
re-validate every image on every visit. New uploads get a long TTL from
AWS_S3_OBJECT_PARAMETERS, but files that predate that setting keep whatever
metadata they were uploaded with -- this command fixes those in place.

S3 has no "edit metadata" verb; the way to do it is to copy an object onto
itself with MetadataDirective=REPLACE. That rewrites the metadata without
moving the bytes, so the public URL does not change.

    python manage.py restamp_media_cache --dry-run
    python manage.py restamp_media_cache
"""

import mimetypes
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

DEFAULT_CACHE_CONTROL = "public, max-age=31536000"

# Supabase's S3 gateway reports application/octet-stream on HEAD regardless of
# what the object API serves, so the extension is the trustworthy source. Taking
# the HEAD value at face value and writing it back strips the real mimetype off
# every object -- which breaks image transformation and inline display.
EXTENSION_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".avif": "image/avif",
    ".heic": "image/heic",
    ".pdf": "application/pdf",
}


def content_type_for(key, head_value=None):
    """Best-known MIME type for an object key."""
    ext = os.path.splitext(key)[1].lower()
    if ext in EXTENSION_TYPES:
        return EXTENSION_TYPES[ext]
    guessed, _ = mimetypes.guess_type(key)
    if guessed:
        return guessed
    if head_value and head_value != "application/octet-stream":
        return head_value
    return "application/octet-stream"


class Command(BaseCommand):
    help = "Set Cache-Control on existing objects in the Supabase media bucket."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List what would change without writing anything.",
        )
        parser.add_argument(
            "--prefix",
            default="",
            help="Only touch keys under this prefix (e.g. uploads/).",
        )
        parser.add_argument(
            "--cache-control",
            default=DEFAULT_CACHE_CONTROL,
            help=f"Header value to apply. Defaults to '{DEFAULT_CACHE_CONTROL}'.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Stop after this many objects. 0 means no limit.",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "USE_SUPABASE_STORAGE", False):
            raise CommandError(
                "Supabase storage is not configured. Set SUPABASE_S3_ENDPOINT, "
                "SUPABASE_S3_ACCESS_KEY_ID and SUPABASE_S3_SECRET_ACCESS_KEY "
                "in your .env first."
            )

        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError as exc:  # pragma: no cover
            raise CommandError(f"boto3 is required: {exc}")

        dry_run = options["dry_run"]
        prefix = options["prefix"]
        cache_control = options["cache_control"]
        limit = options["limit"]
        bucket = settings.AWS_STORAGE_BUCKET_NAME

        client = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
            config=boto3.session.Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )

        mode = "DRY RUN" if dry_run else "APPLY"
        self.stdout.write(f"[{mode}] bucket={bucket} prefix={prefix or '(all)'}")
        self.stdout.write(f"[{mode}] Cache-Control -> {cache_control}\n")

        scanned = updated = skipped = failed = 0
        paginator = client.get_paginator("list_objects_v2")

        try:
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
            for page in pages:
                for obj in page.get("Contents", []):
                    if limit and scanned >= limit:
                        break
                    key = obj["Key"]
                    if key.endswith("/"):
                        continue
                    scanned += 1

                    try:
                        head = client.head_object(Bucket=bucket, Key=key)
                    except ClientError as exc:
                        failed += 1
                        self.stderr.write(f"  head failed {key}: {exc}")
                        continue

                    current = head.get("CacheControl") or "(none)"
                    current_type = head.get("ContentType") or "(none)"
                    wanted_type = content_type_for(key, current_type)
                    if current == cache_control and current_type == wanted_type:
                        skipped += 1
                        continue

                    self.stdout.write(
                        f"  {obj['Size'] / 1024:>9,.0f} KB  {current:<28} "
                        f"{current_type} -> {wanted_type}  {key}"
                    )
                    if dry_run:
                        continue

                    try:
                        # ContentType must be restated; REPLACE drops anything
                        # not passed in here. It is derived from the key rather
                        # than echoed back from HEAD -- see content_type_for.
                        client.copy_object(
                            Bucket=bucket,
                            Key=key,
                            CopySource={"Bucket": bucket, "Key": key},
                            MetadataDirective="REPLACE",
                            CacheControl=cache_control,
                            ContentType=wanted_type,
                            Metadata=head.get("Metadata", {}),
                        )
                        updated += 1
                    except ClientError as exc:
                        failed += 1
                        self.stderr.write(f"  copy failed {key}: {exc}")
                if limit and scanned >= limit:
                    break
        except ClientError as exc:
            raise CommandError(f"Could not list bucket '{bucket}': {exc}")

        self.stdout.write("")
        summary = (
            f"scanned={scanned} "
            f"{'would update' if dry_run else 'updated'}={scanned - skipped - failed} "
            f"already-correct={skipped} failed={failed}"
        )
        if failed:
            self.stdout.write(self.style.WARNING(summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))

        if dry_run and scanned:
            self.stdout.write("\nRe-run without --dry-run to apply.")
