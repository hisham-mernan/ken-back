"""Allow bookings to be made without an account.

access_token is added in three steps on purpose: a callable default on a unique
field applies the SAME value to every existing row during the migration, which
would trip the unique constraint. So it is added nullable and non-unique, filled
row by row, then tightened.
"""

import uuid

from django.db import migrations, models
import django.db.models.deletion


def fill_access_tokens(apps, schema_editor):
    Booking = apps.get_model("products", "Booking")
    for pk in Booking.objects.filter(access_token__isnull=True).values_list(
        "pk", flat=True
    ).iterator():
        Booking.objects.filter(pk=pk).update(access_token=uuid.uuid4())


def clear_access_tokens(apps, schema_editor):
    Booking = apps.get_model("products", "Booking")
    Booking.objects.update(access_token=None)


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0003_alter_availabledateevent_date_and_more"),
    ]

    operations = [
        # A guest booking has no account behind it.
        migrations.AlterField(
            model_name="booking",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="accounts.user",
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="guest_name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="guest_email",
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="guest_phone",
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="guest_id_num",
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        # Step 1: nullable, not yet unique.
        migrations.AddField(
            model_name="booking",
            name="access_token",
            field=models.UUIDField(blank=True, db_index=True, editable=False, null=True),
        ),
        # Step 2: give every existing row its own value.
        migrations.RunPython(fill_access_tokens, clear_access_tokens),
        # Step 3: now the constraint can hold.
        migrations.AlterField(
            model_name="booking",
            name="access_token",
            field=models.UUIDField(
                blank=True,
                db_index=True,
                default=uuid.uuid4,
                editable=False,
                null=True,
                unique=True,
            ),
        ),
    ]
