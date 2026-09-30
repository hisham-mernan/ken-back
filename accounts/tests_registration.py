"""Registering with a Saudi national ID.

id_num was a 32-bit integer. A Saudi national ID is ten digits and a
resident's begins with 2, so roughly 85% of them are above 2147483647 and were
refused at registration -- the API answered "Ensure this value is less than or
equal to 2147483647." and the site rendered that as "an unexpected error".
Those customers could not open an account at all.
"""
from django.test import TestCase

from .models import User
# UserSerializer is what UserRegistrationView registers through.
from .serializers import UserSerializer

# Just above the old 32-bit ceiling, which is where resident IDs live.
RESIDENT_ID = 2900000001
CITIZEN_ID = 1900000001
INT32_MAX = 2147483647


def registration_payload(**overrides):
    payload = {
        "full_name": "Sadeen Alkhulaqi",
        "email": "sadeen@example.invalid",
        "phone": "+966500000911",
        "id_num": RESIDENT_ID,
        "password": "Str0ng!Passw0rd",
        "role": "guest",
    }
    payload.update(overrides)
    return payload


class NationalIdRangeTests(TestCase):
    def test_a_resident_id_is_above_the_old_ceiling(self):
        """Guards the premise: without this the other tests prove nothing."""
        self.assertGreater(RESIDENT_ID, INT32_MAX)
        self.assertLess(CITIZEN_ID, INT32_MAX)

    def test_the_column_can_hold_a_ten_digit_id_on_postgres(self):
        """The one that actually catches a regression here.

        These tests run on SQLite, which has no fixed integer width, so Django
        attaches no range validator and a 32-bit field happily accepts a
        ten-digit ID locally. Production is PostgreSQL, where it does not.
        Asking PostgreSQL's own table of ranges what this field's type holds
        reproduces the production constraint without a PostgreSQL test
        database -- and fails if the field is ever narrowed back.
        """
        from django.db.backends.base.operations import BaseDatabaseOperations

        internal_type = User._meta.get_field("id_num").get_internal_type()
        _, largest = BaseDatabaseOperations.integer_field_ranges[internal_type]
        self.assertGreaterEqual(
            largest, 9999999999,
            "{} tops out at {} on PostgreSQL, below a ten-digit national ID"
            .format(internal_type, largest))

    def test_the_field_accepts_a_resident_id(self):
        user = User.objects.create(email="r@example.invalid", full_name="R",
                                   role="guest", phone="+966500000912",
                                   id_num=RESIDENT_ID)
        # full_clean runs the field's own range validator, which is what
        # refused these IDs before the column was widened.
        user.full_clean(exclude=["password"])
        self.assertEqual(User.objects.get(pk=user.pk).id_num, RESIDENT_ID)

    def test_registration_accepts_a_resident_id(self):
        serializer = UserSerializer(data=registration_payload())
        self.assertTrue(serializer.is_valid(),
                        "a resident's ID must not be rejected: {}".format(serializer.errors))

    def test_registration_still_accepts_a_citizen_id(self):
        serializer = UserSerializer(
            data=registration_payload(id_num=CITIZEN_ID,
                                      email="citizen@example.invalid"))
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_the_serializer_sets_no_upper_bound_below_a_ten_digit_id(self):
        """The rejection came from the field's own range, not a custom rule."""
        field = UserSerializer().fields["id_num"]
        maximum = getattr(field, "max_value", None)
        if maximum is not None:
            self.assertGreaterEqual(maximum, 9999999999)

    def test_a_duplicate_id_is_still_refused(self):
        User.objects.create(email="first@example.invalid", full_name="First",
                            id_num=RESIDENT_ID)
        serializer = UserSerializer(data=registration_payload())
        self.assertFalse(serializer.is_valid(),
                         "the same national ID must not register twice")
        self.assertIn("id_num", serializer.errors)
