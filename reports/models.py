import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


def caminho_foto(instance, filename: str) -> str:
    """Nome aleatório: o nome enviado pelo usuário nunca é usado (RNF02)."""
    hoje = timezone.localdate()
    return f"demandas/{hoje:%Y/%m}/{uuid.uuid4().hex}.jpg"


class Categoria(models.Model):
    class Grupo(models.TextChoices):
        SANEAMENTO = "saneamento", "Saneamento"
        PAVIMENTACAO = "pavimentacao", "Pavimentação"

    nome = models.CharField(max_length=60, unique=True)
    icone = models.CharField(max_length=8, default="⚠️")
    grupo = models.CharField(max_length=20, choices=Grupo.choices)
    cor_mapa = models.CharField(max_length=7, default="#0E3A5B")
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["grupo", "nome"]

    def __str__(self) -> str:
        return self.nome


class Demanda(models.Model):
    class Status(models.TextChoices):
        RECEBIDO = "recebido", "Recebido"
        LEVADO = "levado_prefeitura", "Levado à prefeitura"
        RESOLVIDO = "resolvido", "Resolvido"

    ORDEM_STATUS = [Status.RECEBIDO, Status.LEVADO, Status.RESOLVIDO]

    protocolo = models.CharField(max_length=20, unique=True, editable=False)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="demandas")
    descricao = models.CharField(max_length=500)
    foto = models.ImageField(upload_to=caminho_foto)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    ponto_referencia = models.CharField(max_length=150, blank=True)
    nome_morador = models.CharField(max_length=80)
    telefone_morador = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEBIDO)
    total_afetados = models.PositiveIntegerField(default=1)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["categoria", "status"]),
            models.Index(fields=["criado_em"]),
        ]

    def __str__(self) -> str:
        return f"{self.protocolo} – {self.categoria}"

    def clean(self):
        if self.latitude is None and not self.ponto_referencia:
            raise ValidationError("Informe a localização pelo GPS ou a rua e um ponto de referência.")

    @property
    def indice_status(self) -> int:
        return self.ORDEM_STATUS.index(self.status)

    @property
    def proximo_status(self):
        idx = self.ORDEM_STATUS.index(self.status)
        return self.ORDEM_STATUS[idx + 1] if idx + 1 < len(self.ORDEM_STATUS) else None

    def save(self, *args, **kwargs):
        if not self.protocolo:
            with transaction.atomic():
                ano = timezone.localdate().year
                ultimo = (
                    Demanda.objects.select_for_update()
                    .filter(protocolo__startswith=f"SAF-{ano}-")
                    .order_by("-protocolo")
                    .values_list("protocolo", flat=True)
                    .first()
                )
                seq = int(ultimo.rsplit("-", 1)[1]) + 1 if ultimo else 1
                self.protocolo = f"SAF-{ano}-{seq:04d}"
                super().save(*args, **kwargs)
                HistoricoStatus.objects.create(demanda=self, status_anterior="", status_novo=self.status)
            return
        super().save(*args, **kwargs)

    def avancar_status(self, usuario, observacao: str = "") -> None:
        """RF04 – o status só avança na ordem Recebido → Levado à prefeitura → Resolvido."""
        novo = self.proximo_status
        if novo is None:
            raise ValidationError("Esta demanda já está resolvida.")
        anterior = self.status
        self.status = novo
        with transaction.atomic():
            self.save(update_fields=["status", "atualizado_em"])
            HistoricoStatus.objects.create(
                demanda=self,
                status_anterior=anterior,
                status_novo=novo,
                observacao=observacao[:300],
                alterado_por=usuario,
            )


class Apoio(models.Model):
    """RF06 – morador que indicou 'Também sou afetado'. O telefone é guardado só como HMAC."""

    demanda = models.ForeignKey(Demanda, on_delete=models.CASCADE, related_name="apoios")
    telefone_hash = models.CharField(max_length=64)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["demanda", "telefone_hash"], name="apoio_unico_por_telefone"),
        ]


class HistoricoStatus(models.Model):
    demanda = models.ForeignKey(Demanda, on_delete=models.CASCADE, related_name="historico")
    status_anterior = models.CharField(max_length=20, blank=True)
    status_novo = models.CharField(max_length=20, choices=Demanda.Status.choices)
    observacao = models.CharField(max_length=300, blank=True)
    alterado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    alterado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["alterado_em"]
        verbose_name = "histórico de status"
        verbose_name_plural = "histórico de status"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("O histórico de status não pode ser alterado.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("O histórico de status não pode ser apagado.")
