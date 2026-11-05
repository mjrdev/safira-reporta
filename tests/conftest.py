from io import BytesIO

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from reports.models import Categoria, Demanda


@pytest.fixture(autouse=True)
def _limpar_cache_e_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.SECURE_SSL_REDIRECT = False
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    cache.clear()
    yield
    cache.clear()


def gerar_imagem(formato="JPEG", tamanho=(800, 600), exif_gps=False) -> bytes:
    img = Image.new("RGB", tamanho, (120, 140, 100))
    saida = BytesIO()
    kwargs = {}
    if exif_gps and formato == "JPEG":
        exif = Image.Exif()
        exif[0x010F] = "FabricanteTeste"  # Make
        exif[0x8825] = {1: "S", 2: (2.0, 31.0, 0.0)}  # GPSInfo
        kwargs["exif"] = exif
    img.save(saida, format=formato, **kwargs)
    return saida.getvalue()


@pytest.fixture
def foto_jpg():
    return SimpleUploadedFile("rua.jpg", gerar_imagem(), content_type="image/jpeg")


@pytest.fixture
def esgoto(db):
    return Categoria.objects.get(nome="Esgoto a céu aberto")


@pytest.fixture
def buraco(db):
    return Categoria.objects.get(nome="Buraco")


@pytest.fixture
def demanda(db, esgoto):
    return Demanda.objects.create(
        categoria=esgoto,
        descricao="Esgoto correndo na frente da casa 40.",
        foto=SimpleUploadedFile("x.jpg", gerar_imagem(), content_type="image/jpeg"),
        latitude="-2.530000",
        longitude="-44.150000",
        ponto_referencia="Rua Fictícia A, perto da praça",
        nome_morador="Cláudia",
        telefone_morador="98900000000",
    )


@pytest.fixture
def operador(django_user_model):
    return django_user_model.objects.create_user(username="luiz", password="SenhaForte#2026")


@pytest.fixture
def cliente_logado(client, operador):
    client.force_login(operador)
    return client
