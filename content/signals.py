"""Drop the cached content lists when the content behind them changes.

Two list endpoints cache their response for half an hour, and nothing cleared
those caches when the records were edited. An admin who changed the about-us
copy or swapped an image saw the site unchanged for up to thirty minutes and
had no way to tell whether the edit had saved at all -- it had; the list was
simply being served from cache while the detail endpoint returned the new
values.

Mirrors products/signals.py, which already does this for the hut and event
lists.
"""
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import AboutUs, FAQ


@receiver([post_save, post_delete], sender=AboutUs)
def invalidate_about_us_cache(sender, instance, **kwargs):
    cache.delete("content_about_us_list")


@receiver([post_save, post_delete], sender=FAQ)
def invalidate_faq_cache(sender, instance, **kwargs):
    cache.delete("content_faq_list")
