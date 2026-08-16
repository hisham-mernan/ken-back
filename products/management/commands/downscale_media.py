"""Downscale the original images already sitting in the Supabase bucket.

The uploads are straight-off-the-camera files -- 45 hut photos at 12-14 MB each,
up to 5680x2988. Nothing renders anywhere near that size. Supabase's on-the-fly
image transformation would solve delivery without touching them, but it is a
paid per-project feature; this achieves the same result without it.

Every object is rewritten UNDER ITS EXISTING KEY, in its original format. The
public URL, the path stored in Postgres, and the file extension are all
unchanged, so nothing needs re-uploading or re-linking -- the same URLs simply
start returning smaller bytes.

Objects are downloaded to --backup-dir before being overwritten.

    python manage.py downscale_media --dry-run
    python manage.py downscale_media --backup-dir C:\\Users\\me\\ken_backup
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.image_optimization import optimize_image_bytes

CACHE_CONTROL = "public, max-age=31536000"

EXTENSION_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class Command(BaseCommand):
    help = "Downscale oversized originals in the Supabase bucket, in place."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--prefix", default="")
        parser.add_argument(
            "--backup-dir",
            default="",
            help="Directory to save originals into. Required unless --dry-run.",
        )
        parser.add_argument(
            "--max-edge",
            type=int,
            default=2560,
            help="Longest side to keep. Default 2560.",
        )
        parser.add_argument("--limit", type=int, default=0)

    def handle(self, *args, **options):
        if not getattr(settings, "USE_SUPABASE_STORAGE", False):
            raise CommandError(
                "Supabase storage is not configured; set the SUPABASE_S3_* "
                "variables in your .env first."
            )

        dry_run = options["dry_run"]
        backup_dir = options["backup_dir"]
        max_edge = options["max_edge"]
        limit = options["limit"]
        prefix = options["prefix"]

        if not dry_run and not backup_dir:
            raise CommandError(
                "--backup-dir is required when actually rewriting objects. "
                "Originals cannot be recovered from Supabase once overwritten."
            )
        if backup_dir:
            os.makedirs(backup_dir, exist_ok=True)

        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError as exc:  # pragma: no cover
            raise CommandError(f"boto3 is required: {exc}")

        bucket = settings.AWS_STORAGE_BUCKET_NAME
        client = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
            config=boto3.session.Config(
                signature_version="s3v4", s3={"addressing_style": "path"}
            ),
        )

        mode = "DRY RUN" if dry_run else "APPLY"
        self.stdout.write(f"[{mode}] bucket={bucket} max-edge={max_edge}px")
        if backup_dir:
            self.stdout.write(f"[{mode}] originals -> {backup_dir}")
        self.stdout.write("")

        scanned = rewritten = skipped = failed = 0
        before_total = after_total = 0

        try:
            pages = client.get_paginator("list_objects_v2").paginate(
                Bucket=bucket, Prefix=prefix
            )
            for page in pages:
                for obj in page.get("Contents", []):
                    if limit and scanned >= limit:
                        break
                    key = obj["Key"]
                    if key.endswith("/"):
                        continue
                    scanned += 1

                    try:
                        body = client.get_object(Bucket=bucket, Key=key)["Body"].read()
                    except ClientError as exc:
                        failed += 1
                        self.stderr.write(f"  download failed {key}: {exc}")
                        continue

                    result = optimize_image_bytes(
                        body, key, max_edge=max_edge, preserve_format=True
                    )
                    if result is None:
                        skipped += 1
                        continue

                    new_bytes, _ = result
                    before_total += len(body)
                    after_total += len(new_bytes)
                    saved = (1 - len(new_bytes) / len(body)) * 100
                    self.stdout.write(
                        f"  {len(body) / 1048576:>7.2f} MB -> "
                        f"{len(new_bytes) / 1048576:>6.2f} MB  -{saved:4.1f}%  {key}"
                    )
                    if dry_run:
                        continue

                    # Keep the original on disk BEFORE the object is replaced.
                    local = os.path.join(backup_dir, key.replace("/", os.sep))
                    os.makedirs(os.path.dirname(local), exist_ok=True)
                    with open(local, "wb") as fh:
                        fh.write(body)

                    ext = os.path.splitext(key)[1].lower()
                    try:
                        client.put_object(
                            Bucket=bucket,
                            Key=key,  # identical key -- URL does not change
                            Body=new_bytes,
                            ContentType=EXTENSION_TYPES.get(
                                ext, "application/octet-stream"
                            ),
                            CacheControl=CACHE_CONTROL,
                        )
                        rewritten += 1
                    except ClientError as exc:
                        failed += 1
                        self.stderr.write(f"  upload failed {key}: {exc}")
                if limit and scanned >= limit:
                    break
        except ClientError as exc:
            raise CommandError(f"Could not list bucket '{bucket}': {exc}")

        self.stdout.write("")
        if before_total:
            self.stdout.write(
                f"{before_total / 1048576:.1f} MB -> {after_total / 1048576:.1f} MB "
                f"({(1 - after_total / before_total) * 100:.1f}% smaller)"
            )
        summary = (
            f"scanned={scanned} "
            f"{'would rewrite' if dry_run else 'rewritten'}={rewritten if not dry_run else scanned - skipped - failed} "
            f"left-alone={skipped} failed={failed}"
        )
        self.stdout.write(
            self.style.WARNING(summary) if failed else self.style.SUCCESS(summary)
        )
        if dry_run:
            self.stdout.write("\nRe-run with --backup-dir <path> to apply.")
