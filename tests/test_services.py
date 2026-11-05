"""Testes unitários dos serviços: telefone, proximidade, apoio e foto (RF06, RNF02)."""

from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from reports import services
from reports.models import Demanda

from .conftest import gerar_imagem


@pytest.mark.parametrize(
    "entrada,esperado",
    [("(98) 90000-0000", "98900000000"), ("+55 98 3333-4444", "9833334444"), ("98900000000", "98900000000")],
)
def test_normalizar_telefone_aceita_formatos_comuns(entrada, esperado):
    assert services.normalizar_telefone(entrada) == esperado


@pytest.mark.parametrize("entrada", ["", "9000", "(98) 9000", "abc"])
def test_normalizar_telefone_recusa_incompleto(entrada):
    with pytest.raises(ValidationError):
        services.normalizar_telefone(entrada)


def test_hash_telefone_e_estavel_e_nao_expoe_numero(settings):
    settings.PHONE_HASH_KEY = "chave-teste"
    h1 = services.hash_telefone("(98) 90000-0000")
    h2 = services.hash_telefone("98900000000")
    assert h1 == h2 and len(h1) == 64 and "98900000000" not in h1


def test_distancia_metros_aproximada():
    # ~0,001 grau de latitude ≈ 111 m
    d = services.distancia_metros(-2.530, -44.150, -2.531, -44.150)
    assert 105 < d < 117


@pytest.mark.django_db
def test_demandas_proximas_encontra_mesma_categoria_dentro_do_raio(demanda, esgoto, buraco):
    perto = services.demandas_proximas(esgoto, -2.5303, -44.1502)  # ~40 m
    longe = services.demandas_proximas(esgoto, -2.5400, -44.1500)  # ~1,1 km
    outra_categoria = services.demandas_proximas(buraco, -2.5303, -44.1502)
    assert perto == [demanda]
    assert longe == []
    assert outra_categoria == []


@pytest.mark.django_db
def test_demandas_proximas_ignora_resolvidas(demanda, esgoto, operador):
    demanda.avancar_status(operador)
    demanda.avancar_status(operador)
    assert services.demandas_proximas(esgoto, -2.5303, -44.1502) == []


@pytest.mark.django_db
def test_registrar_apoio_soma_afetados_e_bloqueia_repeticao(demanda):
    services.registrar_apoio(demanda, "98922223333")
    assert demanda.total_afetados == 2
    with pytest.raises(ValidationError):
        services.registrar_apoio(demanda, "(98) 92222-3333")
    demanda.refresh_from_db()
    assert demanda.total_afetados == 2


@pytest.mark.django_db
def test_registrar_apoio_recusa_demanda_resolvida(demanda, operador):
    demanda.avancar_status(operador)
    demanda.avancar_status(operador)
    with pytest.raises(ValidationError):
        services.registrar_apoio(demanda, "98922223333")


def test_processar_foto_remove_exif_e_converte_para_jpeg():
    arquivo = SimpleUploadedFile("f.jpg", gerar_imagem(exif_gps=True, tamanho=(3000, 2000)), "image/jpeg")
    saida = services.processar_foto(arquivo)
    img = Image.open(BytesIO(saida.read()))
    assert img.format == "JPEG"
    assert max(img.size) <= services.FOTO_MAX_LADO
    assert len(img.getexif()) == 0


def test_processar_foto_aceita_png():
    arquivo = SimpleUploadedFile("f.png", gerar_imagem("PNG"), "image/png")
    assert services.processar_foto(arquivo).name == "foto.jpg"


def test_processar_foto_recusa_arquivo_que_nao_e_imagem():
    falso = SimpleUploadedFile("shell.jpg", b"<?php system($_GET['c']); ?>", "image/jpeg")
    with pytest.raises(ValidationError):
        services.processar_foto(falso)


def test_processar_foto_recusa_gif():
    arquivo = SimpleUploadedFile("f.gif", gerar_imagem("GIF"), "image/gif")
    with pytest.raises(ValidationError):
        services.processar_foto(arquivo)


def test_processar_foto_recusa_maior_que_2mb():
    grande = SimpleUploadedFile("g.jpg", b"0" * (services.FOTO_MAX_BYTES + 1), "image/jpeg")
    with pytest.raises(ValidationError):
        services.processar_foto(grande)


@pytest.mark.django_db
def test_foto_salva_com_nome_aleatorio(demanda):
    assert demanda.foto.name.startswith("demandas/")
    assert "x.jpg" not in demanda.foto.name
    assert Demanda.objects.get(pk=demanda.pk).foto.name.endswith(".jpg")
