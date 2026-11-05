from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ApoioForm, ConsultaForm, DemandaForm
from .models import Demanda
from .services import demandas_proximas, registrar_apoio


def _ip(request) -> str:
    return request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")).split(",")[0].strip()


def home(request):
    totais = Demanda.objects.aggregate(
        registrados=Count("id"),
        levados=Count("id", filter=~Q(status=Demanda.Status.RECEBIDO)),
    )
    return render(request, "reports/home.html", {"totais": totais, "consulta_form": ConsultaForm()})


def privacidade(request):
    return render(request, "reports/privacidade.html")


def registrar(request):
    """RF01 + RF06 – registro do problema, com oferta de 'Também sou afetado'."""
    proximas = []
    if request.method == "POST":
        form = DemandaForm(request.POST, request.FILES)
        if form.is_valid():
            dados = form.cleaned_data
            confirmou_novo = request.POST.get("confirmar_novo") == "1"
            if not confirmou_novo:
                proximas = demandas_proximas(dados["categoria"], dados["latitude"], dados["longitude"])
            if proximas:
                messages.warning(request, "Já registraram este problema aqui perto. Você também é afetado?")
                # A foto precisa ser enviada de novo se a pessoa optar por novo registro
                return render(
                    request,
                    "reports/registrar.html",
                    {
                        "form": form,
                        "proximas": proximas,
                        "apoio_form": ApoioForm(initial={"telefone": dados["telefone_morador"]}),
                    },
                )
            demanda = form.save()
            request.session["ultimo_protocolo"] = demanda.protocolo
            return redirect("confirmacao", protocolo=demanda.protocolo)
    else:
        form = DemandaForm()
    return render(request, "reports/registrar.html", {"form": form, "proximas": proximas})


@require_POST
def apoiar(request, protocolo):
    demanda = get_object_or_404(Demanda, protocolo=protocolo)
    form = ApoioForm(request.POST)
    if form.is_valid():
        try:
            registrar_apoio(demanda, form.cleaned_data["telefone"])
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
            return redirect("consulta_protocolo", protocolo=protocolo)
        messages.success(request, "Pronto! Seu apoio foi somado a este pedido.")
        return redirect("confirmacao", protocolo=protocolo)
    messages.error(request, "Telefone incompleto. Digite o DDD e o número.")
    return redirect("consulta_protocolo", protocolo=protocolo)


def confirmacao(request, protocolo):
    demanda = get_object_or_404(Demanda.objects.select_related("categoria"), protocolo=protocolo)
    return render(request, "reports/resultado.html", {"demanda": demanda, "novo": True})


def consultar(request):
    """RF02 – consulta pública por protocolo, com limite por IP."""
    chave = f"consulta:{_ip(request)}"
    tentativas = cache.get(chave, 0)
    if tentativas >= settings.CONSULTA_MAX_POR_MINUTO:
        return HttpResponse("Muitas consultas seguidas. Aguarde um minuto e tente de novo.", status=429)
    cache.set(chave, tentativas + 1, 60)

    form = ConsultaForm(request.GET or None)
    if form.is_valid():
        return redirect("consulta_protocolo", protocolo=form.cleaned_data["protocolo"])
    return render(request, "reports/consultar.html", {"form": form})


def consulta_protocolo(request, protocolo):
    demanda = Demanda.objects.select_related("categoria").filter(protocolo=protocolo.upper()).first()
    if demanda is None:
        return render(
            request, "reports/consultar.html", {"form": ConsultaForm(), "nao_encontrado": protocolo}, status=404
        )
    return render(request, "reports/resultado.html", {"demanda": demanda, "novo": False, "apoio_form": ApoioForm()})


def resolvidos(request):
    """RF08 – página pública de problemas resolvidos, sem dados pessoais."""
    demandas = Demanda.objects.filter(status=Demanda.Status.RESOLVIDO).select_related("categoria")[:50]
    return render(request, "reports/resolvidos.html", {"demandas": demandas})
