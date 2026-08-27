from django.apps import AppConfig


class ContentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "content"

    def ready(self):
        # Wires the cache invalidation. Without it an edit is saved but the
        # site keeps serving the previous version for up to half an hour.
        from . import signals  # noqa: F401
