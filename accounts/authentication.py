from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from django.utils import timezone
import datetime
from rest_framework_simplejwt.exceptions import AuthenticationFailed

# class CustomAuthenticationFailed(AuthenticationFailed):
#     def __init__(self, detail):
#         self.detail = {"error": detail}


# class CustomJWTAuthentication(JWTAuthentication):
#     def get_user(self, validated_token):
#         user = super().get_user(validated_token)

#         token_iat = validated_token.get('iat', None)  

#         if token_iat and user.change_password_at:
#             issued_time = datetime.datetime.fromtimestamp(token_iat, tz=timezone.utc)
#             if issued_time < user.change_password_at:
#                 raise CustomAuthenticationFailed('Token expired')

#         return user
from django.utils import timezone
import datetime
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

class CustomAuthenticationFailed(AuthenticationFailed):
    def __init__(self, detail):
        self.detail = {"error": detail}


class CustomJWTAuthentication(JWTAuthentication):
    """
    • If the user hasn’t scheduled a password change → normal JWT behaviour.
    • If a change is scheduled in the future (grace‑period)  →
      tokens stay valid until that moment.
    • Once we are *past* change_password_at →
      only tokens issued **after** that moment are accepted.
    """
    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        token_iat = validated_token.get("iat")      # UNIX epoch seconds
        if not token_iat or not user.change_password_at:
            return user                             # nothing extra to check

        issued_time = datetime.datetime.fromtimestamp(token_iat,
                                                     tz=timezone.utc)

        # Are we already past the scheduled change?
        if timezone.now() >= user.change_password_at:
            # Tokens minted *before* the cut‑off are no longer valid
            if issued_time < user.change_password_at:
                raise CustomAuthenticationFailed("Token expired")

        # Still inside the grace period → token is fine
        return user
