from django.apps import AppConfig

from threading import Thread
# from .schedular import run_scheduler
class ProductsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "products"
    def ready(self):
        import products.signals
        import products.scheduler
        # scheduler_thread = Thread(target=run_scheduler, daemon=True)
        # scheduler_thread.start()
        # print("Scheduler thread started.")
        
        
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
