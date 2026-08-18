"""The login endpoint's error contract.

Every failure used to be flattened into HTTP 500 with a stringified Python
dict and a full traceback, so the website could not tell "wrong password"
from "account not verified" and showed "Something went wrong" for both.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

PASSWORD = "pw-not-a-real-secret"


class LoginErrorContractTests(TestCase):
    url = "/login/"

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="login-test@example.invalid", password=PASSWORD
        )
        self.user.is_verfied = True
        self.user.save()

    def post(self, **body):
        return self.client.post(self.url, body, content_type="application/json")

    def test_unknown_user_is_a_400_the_frontend_can_read(self):
        r = self.post(email="nobody@example.invalid", password=PASSWORD)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json().get("email"), ["User not found."])

    def test_wrong_password_is_a_400_the_frontend_can_read(self):
        r = self.post(email=self.user.email, password="wrong-password")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json().get("password"), ["Password is not correct."])

    def test_unverified_account_reports_itself_so_otp_can_be_offered(self):
        self.user.is_verfied = False
        self.user.save()
        r = self.post(email=self.user.email, password=PASSWORD)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(
            r.json().get("non_field_errors"), ["This user is not verified."]
        )

    def test_valid_credentials_still_return_a_token(self):
        r = self.post(email=self.user.email, password=PASSWORD)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("token"))

    def test_no_failure_mode_leaks_a_traceback(self):
        for label, body in (
            ("unknown user", {"email": "nobody@example.invalid", "password": PASSWORD}),
            ("wrong password", {"email": self.user.email, "password": "nope"}),
            ("empty payload", {}),
        ):
            with self.subTest(case=label):
                r = self.post(**body)
                self.assertNotIn("traceback", r.content.decode().lower())
