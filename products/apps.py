from django.apps import AppConfig

from threading import Thread
# from .schedular import run_scheduler
class ProductsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "products"
    def ready(self):
        import products.signals
        import products.scheduler
        
        try:
            from products.models import Event
            if not Event.objects.filter(is_active=True).exists():
                from django.core.management import call_command
                call_command('seed_ken_data')
                print("[ProductsConfig] Automatically seeded database with Ken content.")
        except Exception as e:
            pass
        
        
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
