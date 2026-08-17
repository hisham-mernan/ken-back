"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin

from django.urls import path,include
from django.shortcuts import redirect

from core.storage_check import storage_check

urlpatterns = [
    path("admin/", admin.site.urls),
    # TEMPORARY: reports whether the SUPABASE_S3_* variables resolved in the
    # running deployment, and can round-trip a 1x1 PNG through storage.
    # Remove this line and core/storage_check.py once uploads are confirmed.
    path("api/health/storage/", storage_check),
    path("", include('accounts.urls')),
    path("api/products/", include('products.urls')),
    path("api/content/", include('content.urls')),
    path("api/payments/", include('payments.urls')),
    

]
from django.conf import settings
from django.conf.urls.static import static


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)