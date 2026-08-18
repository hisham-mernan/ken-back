from django.apps import AppConfig

from threading import Thread
# from .schedular import run_scheduler
class ProductsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "products"
    def ready(self):
        import products.signals
        import products.scheduler
        # Global pre_save hook that downscales uploaded images (all apps).
        import core.image_optimization

        # Deliberately no auto-seeding here. seed_ken_data begins by deleting
        # every Booking, BookingDate and ticket in the database, and this ran
        # on every process start -- which on Vercel is every cold start -- so
        # deactivating the last Event was enough to wipe live bookings with no
        # one doing anything wrong. Run the command by hand when you actually
        # mean to provision an environment.
        
        
# from django.apps import AppConfig
# from threading import Thread
# from .scheduler import run_scheduler

# class ProductsConfig(AppConfig):
#     default_auto_field = "django.db.models.BigAutoField"
#     name = "products"

#     def ready(self):
#         import products.signals
#         scheduler_thread = Thread(target=run_scheduler, daemon=True)
#         scheduler_thread.start()
#         print("Scheduler thread started.")
