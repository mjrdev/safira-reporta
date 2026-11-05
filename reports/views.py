from django.conf import settings
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ApoioForm, ConsultaForm, DemandaForm, FiltroPainelForm, StatusForm
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


# ---------------------- Painel da associação (RF03, RF04, RF05, RF07) ----------------------


def _filtrar(request):
    form = FiltroPainelForm(request.GET or None)
    qs = Demanda.objects.select_related("categoria")
    if form.is_valid():
        if form.cleaned_data.get("categoria"):
            qs = qs.filter(categoria=form.cleaned_data["categoria"])
        if form.cleaned_data.get("grupo"):
            qs = qs.filter(categoria__grupo=form.cleaned_data["grupo"])
        if form.cleaned_data.get("status"):
            qs = qs.filter(status=form.cleaned_data["status"])
    return form, qs


@login_required
def painel(request):
    form, qs = _filtrar(request)
    pagina = Paginator(qs, 20).get_page(request.GET.get("page"))
    pontos = [
        {
            "lat": float(d.latitude),
            "lon": float(d.longitude),
            "cor": d.categoria.cor_mapa,
            "titulo": f"{d.protocolo} – {d.categoria.nome}",
            "url": f"/painel/demanda/{d.protocolo}/",
        }
        for d in pagina
        if d.latitude is not None
    ]
    return render(
        request,
        "reports/painel/lista.html",
        {"form": form, "pagina": pagina, "pontos": pontos, "query": request.GET.urlencode()},
    )


@login_required
def detalhe(request, protocolo):
    demanda = get_object_or_404(Demanda.objects.select_related("categoria"), protocolo=protocolo)
    return render(request, "reports/painel/detalhe.html", {"demanda": demanda, "status_form": StatusForm()})


@login_required
@require_POST
def avancar_status(request, protocolo):
    demanda = get_object_or_404(Demanda, protocolo=protocolo)
    form = StatusForm(request.POST)
    if form.is_valid():
        try:
            demanda.avancar_status(request.user, form.cleaned_data["observacao"])
            messages.success(request, f"Status atualizado para “{demanda.get_status_display()}”.")
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
    return redirect("detalhe", protocolo=protocolo)


@login_required
def relatorio(request):
    """RF05 – página pronta para impressão/PDF, sem nome nem telefone dos moradores."""
    form, qs = _filtrar(request)
    return render(request, "reports/painel/relatorio.html", {"demandas": qs, "form": form})


# ---------------------- Login com limite de tentativas (RNF01) ----------------------


class LoginView(auth_views.LoginView):
    template_name = "registration/login.html"

    def _chave(self):
        usuario = (self.request.POST.get("username") or "").lower()[:150]
        return f"login:{_ip(self.request)}:{usuario}"

    def post(self, request, *args, **kwargs):
        if cache.get(self._chave(), 0) >= settings.LOGIN_MAX_TENTATIVAS:
            form = self.get_form()
            form.errors.clear()
            form.add_error(None, "Muitas tentativas. Aguarde 15 minutos e tente de novo.")
            return self.render_to_response(self.get_context_data(form=form), status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        chave = self._chave()
        cache.set(chave, cache.get(chave, 0) + 1, settings.LOGIN_BLOQUEIO_SEGUNDOS)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self._chave())
        return super().form_valid(form)
