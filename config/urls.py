import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

ADMIN_PATH = os.environ.get("ADMIN_PATH", "gestao-associacao/")

urlpatterns = [
    path(ADMIN_PATH, admin.site.urls),
    path("", include("reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
