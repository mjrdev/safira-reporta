import re

from django import forms
from django.core.exceptions import ValidationError

from .models import Categoria, Demanda
from .services import normalizar_telefone, processar_foto

# Área aproximada da Grande São Luís, para descartar coordenadas absurdas
LAT_MIN, LAT_MAX = -2.75, -2.40
LON_MIN, LON_MAX = -44.40, -44.05

PROTOCOLO_RE = re.compile(r"^SAF-\d{4}-\d{4,}$")


class DemandaForm(forms.ModelForm):
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.filter(ativa=True),
        widget=forms.RadioSelect,
        empty_label=None,
        error_messages={"required": "Escolha uma categoria para continuar."},
    )

    class Meta:
        model = Demanda
        fields = [
            "categoria",
            "foto",
            "latitude",
            "longitude",
            "ponto_referencia",
            "descricao",
            "nome_morador",
            "telefone_morador",
        ]
        labels = {
            "foto": "Foto do problema",
            "ponto_referencia": "Rua e ponto de referência",
            "descricao": "O que está acontecendo?",
            "nome_morador": "Seu nome",
            "telefone_morador": "Seu telefone (com DDD)",
        }
        widgets = {
            "latitude": forms.HiddenInput,
            "longitude": forms.HiddenInput,
            "descricao": forms.Textarea(attrs={"rows": 3, "maxlength": 500}),
            "foto": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png", "capture": "environment"}),
            "telefone_morador": forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "tel"}),
            "nome_morador": forms.TextInput(attrs={"autocomplete": "name"}),
        }
        error_messages = {
            "foto": {
                "required": "Tire uma foto do problema para continuar.",
                "invalid_image": "A foto precisa ser JPG ou PNG. Tire outra foto ou escolha da galeria.",
            },
            "descricao": {"required": "Conte em poucas palavras o que está acontecendo."},
            "nome_morador": {"required": "Informe seu nome."},
            "telefone_morador": {"required": "Informe seu telefone com DDD."},
        }

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        if foto and hasattr(foto, "size") and not getattr(foto, "_committed", False):
            return processar_foto(foto)
        return foto

    def clean_telefone_morador(self):
        return normalizar_telefone(self.cleaned_data.get("telefone_morador", ""))

    def clean_descricao(self):
        return (self.cleaned_data.get("descricao") or "").strip()

    def clean(self):
        dados = super().clean()
        lat, lon = dados.get("latitude"), dados.get("longitude")
        if (lat is None) != (lon is None):
            raise ValidationError("Localização incompleta. Toque de novo em “Usar minha localização”.")
        if lat is not None and not (LAT_MIN <= float(lat) <= LAT_MAX and LON_MIN <= float(lon) <= LON_MAX):
            raise ValidationError("A localização parece estar fora da região. Confira o ponto ou escreva a rua.")
        if lat is None and not dados.get("ponto_referencia"):
            self.add_error("ponto_referencia", "Use sua localização ou escreva a rua e um ponto de referência.")
        return dados


class ApoioForm(forms.Form):
    telefone = forms.CharField(
        label="Seu telefone (com DDD)",
        max_length=20,
        widget=forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "tel"}),
    )

    def clean_telefone(self):
        return normalizar_telefone(self.cleaned_data["telefone"])


class ConsultaForm(forms.Form):
    protocolo = forms.CharField(label="Número do protocolo", max_length=20)

    def clean_protocolo(self):
        valor = self.cleaned_data["protocolo"].strip().upper()
        if not PROTOCOLO_RE.match(valor):
            raise ValidationError("O protocolo tem o formato SAF-2026-0042.")
        return valor


class FiltroPainelForm(forms.Form):
    categoria = forms.ModelChoiceField(queryset=Categoria.objects.all(), required=False, empty_label="Todas")
    grupo = forms.ChoiceField(choices=[("", "Todos")] + list(Categoria.Grupo.choices), required=False)
    status = forms.ChoiceField(choices=[("", "Todos")] + list(Demanda.Status.choices), required=False)


class StatusForm(forms.Form):
    observacao = forms.CharField(label="Observação (opcional)", max_length=300, required=False)
