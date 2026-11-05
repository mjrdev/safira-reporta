import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

ADMIN_PATH = os.environ.get("ADMIN_PATH", "gestao-associacao/")

urlpatterns = [
    path(ADMIN_PATH, admin.site.urls),
    path("", include("reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif "default" not in settings.STORAGES or "s3" not in settings.STORAGES["default"]["BACKEND"]:  # pragma: no cover
    # Sem bucket configurado, o próprio Django entrega as fotos (suficiente para o MVP;
    # em produção o recomendado é o Supabase Storage via variáveis AWS_*).
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]
