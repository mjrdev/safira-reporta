"""Regras de negócio que não pertencem a um único model."""

import hashlib
import hmac
import math
import re
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import IntegrityError, transaction
from django.db.models import F
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import Apoio, Demanda

RAIO_PROXIMIDADE_METROS = 100
FOTO_MAX_BYTES = 2 * 1024 * 1024
FOTO_MAX_LADO = 1280
FORMATOS_PERMITIDOS = {"JPEG", "PNG"}


def normalizar_telefone(valor: str) -> str:
    digitos = re.sub(r"\D", "", valor or "")
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]
    if len(digitos) not in (10, 11):
        raise ValidationError("Telefone incompleto. Digite o DDD e o número.")
    return digitos


def hash_telefone(telefone: str) -> str:
    chave = settings.PHONE_HASH_KEY.encode()
    return hmac.new(chave, normalizar_telefone(telefone).encode(), hashlib.sha256).hexdigest()


def distancia_metros(lat1, lon1, lat2, lon2) -> float:
    """Distância aproximada (haversine) entre dois pontos, em metros."""
    r = 6_371_000
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = p2 - p1
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def demandas_proximas(categoria, latitude, longitude, raio=RAIO_PROXIMIDADE_METROS):
    """RF06 – demandas abertas da mesma categoria a até `raio` metros."""
    if latitude is None or longitude is None:
        return []
    candidatas = Demanda.objects.filter(categoria=categoria, latitude__isnull=False).exclude(
        status=Demanda.Status.RESOLVIDO
    )
    # Pré-filtro por caixa (~0,002 grau ≈ 220 m) antes do cálculo exato
    delta = Decimal("0.002")
    candidatas = candidatas.filter(
        latitude__range=(Decimal(latitude) - delta, Decimal(latitude) + delta),
        longitude__range=(Decimal(longitude) - delta, Decimal(longitude) + delta),
    )
    return [d for d in candidatas if distancia_metros(latitude, longitude, d.latitude, d.longitude) <= raio]


def registrar_apoio(demanda: Demanda, telefone: str) -> Apoio:
    if demanda.status == Demanda.Status.RESOLVIDO:
        raise ValidationError("Esta demanda já foi resolvida.")
    try:
        with transaction.atomic():
            apoio = Apoio.objects.create(demanda=demanda, telefone_hash=hash_telefone(telefone))
            Demanda.objects.filter(pk=demanda.pk).update(total_afetados=F("total_afetados") + 1)
    except IntegrityError as exc:
        raise ValidationError("Este telefone já apoiou esta demanda.") from exc
    demanda.refresh_from_db(fields=["total_afetados"])
    return apoio


def processar_foto(arquivo):
    """RNF02 – confere se é imagem JPEG/PNG de até 2 MB, remove EXIF e regrava a imagem."""
    if arquivo.size > FOTO_MAX_BYTES:
        raise ValidationError("A foto precisa ter até 2 MB. Tire outra foto ou escolha da galeria.")
    try:
        img = Image.open(arquivo)
        formato = img.format
        img.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError("A foto precisa ser JPG ou PNG. Tire outra foto ou escolha da galeria.") from exc
    if formato not in FORMATOS_PERMITIDOS:
        raise ValidationError("A foto precisa ser JPG ou PNG. Tire outra foto ou escolha da galeria.")

    arquivo.seek(0)
    img = ImageOps.exif_transpose(Image.open(arquivo)).convert("RGB")
    img.thumbnail((FOTO_MAX_LADO, FOTO_MAX_LADO))
    saida = BytesIO()
    img.save(saida, format="JPEG", quality=80, optimize=True)  # regravada sem EXIF
    saida.seek(0)
    return InMemoryUploadedFile(saida, "foto", "foto.jpg", "image/jpeg", saida.getbuffer().nbytes, None)
