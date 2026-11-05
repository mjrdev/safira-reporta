"""Testes de integração do painel da associação e da autenticação (RF03, RF04, RF05, RNF01, RNF02)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from reports.models import Demanda

pytestmark = pytest.mark.django_db

ROTAS_PROTEGIDAS = ["painel", "relatorio"]


@pytest.mark.parametrize("rota", ROTAS_PROTEGIDAS)
def test_painel_sem_login_redireciona_para_login(client, rota):
    resp = client.get(reverse(rota))
    assert resp.status_code == 302
    assert reverse("login") in resp["Location"]


def test_detalhe_e_mudanca_de_status_exigem_login(client, demanda):
    assert client.get(reverse("detalhe", args=[demanda.protocolo])).status_code == 302
    client.post(reverse("avancar_status", args=[demanda.protocolo]))
    demanda.refresh_from_db()
    assert demanda.status == Demanda.Status.RECEBIDO


def test_senha_guardada_como_hash_argon2id(operador):
    senha_no_banco = get_user_model().objects.get(pk=operador.pk).password
    assert senha_no_banco.startswith("argon2$argon2id$")
    assert "SenhaForte#2026" not in senha_no_banco


def test_login_valido_e_invalido(client, operador):
    ruim = client.post(reverse("login"), {"username": "luiz", "password": "errada"})
    assert ruim.status_code == 200 and "_auth_user_id" not in client.session
    bom = client.post(reverse("login"), {"username": "luiz", "password": "SenhaForte#2026"})
    assert bom.status_code == 302 and bom["Location"] == reverse("painel")


def test_login_bloqueia_apos_tentativas_erradas(client, operador, settings):
    settings.LOGIN_MAX_TENTATIVAS = 5
    for _ in range(5):
        client.post(reverse("login"), {"username": "luiz", "password": "errada"})
    resp = client.post(reverse("login"), {"username": "luiz", "password": "SenhaForte#2026"})
    assert resp.status_code == 429
    assert "Muitas tentativas" in resp.text


def test_logout_encerra_sessao(cliente_logado):
    cliente_logado.post(reverse("logout"))
    assert cliente_logado.get(reverse("painel")).status_code == 302


def test_mudanca_de_status_exige_csrf(operador, demanda):
    from django.test import Client

    c = Client(enforce_csrf_checks=True)
    c.force_login(operador)
    resp = c.post(reverse("avancar_status", args=[demanda.protocolo]))
    assert resp.status_code == 403


def test_painel_lista_e_filtra(cliente_logado, demanda, buraco, foto_jpg):
    Demanda.objects.create(
        categoria=buraco,
        descricao="buraco",
        foto=foto_jpg,
        ponto_referencia="Rua B",
        nome_morador="Ana",
        telefone_morador="98911111111",
    )
    tudo = cliente_logado.get(reverse("painel"))
    assert "2 demandas" in tudo.text
    so_saneamento = cliente_logado.get(reverse("painel"), {"grupo": "saneamento"})
    assert "1 demanda" in so_saneamento.text and demanda.protocolo in so_saneamento.text


def test_operador_avanca_status_e_morador_ve_na_consulta(cliente_logado, client, demanda, operador):
    cliente_logado.post(reverse("avancar_status", args=[demanda.protocolo]), {"observacao": "relatório 10/02"})
    demanda.refresh_from_db()
    assert demanda.status == Demanda.Status.LEVADO
    assert demanda.historico.last().alterado_por == operador
    resp = client.get(reverse("consulta_protocolo", args=[demanda.protocolo]))
    assert "Levado à prefeitura" in resp.text


def test_relatorio_tem_dados_do_problema_sem_dados_pessoais(cliente_logado, demanda):
    resp = cliente_logado.get(reverse("relatorio"), {"grupo": "saneamento"})
    assert resp.status_code == 200
    assert demanda.protocolo in resp.text and "Moradores afetados" in resp.text
    assert "Cláudia" not in resp.text and "98900000000" not in resp.text


def test_painel_mostra_dados_pessoais_apenas_para_logado(cliente_logado, demanda):
    resp = cliente_logado.get(reverse("detalhe", args=[demanda.protocolo]))
    assert "Cláudia" in resp.text


def test_mapa_do_painel_tem_papel_e_rotulo_acessiveis(cliente_logado, demanda):
    resp = cliente_logado.get(reverse("painel"))
    assert 'role="region" aria-label="Mapa das demandas filtradas"' in resp.text


def test_saude_responde_ok_sem_login(client, db):
    resp = client.get(reverse("saude"))
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "banco": "ok"}
    assert "no-cache" in resp["Cache-Control"]


def test_saude_retorna_503_quando_o_banco_falha(client, db, monkeypatch):
    from django.db import connection

    def quebrado():
        raise RuntimeError("banco fora")

    monkeypatch.setattr(connection, "cursor", quebrado)
    resp = client.get(reverse("saude"))
    assert resp.status_code == 503
    assert resp.json()["banco"] == "indisponivel"


def test_indicadores_exige_login(client):
    resp = client.get(reverse("indicadores"))
    assert resp.status_code == 302 and reverse("login") in resp["Location"]


def test_indicadores_somam_demandas_apoios_e_status(cliente_logado, demanda, operador):
    from reports.services import registrar_apoio

    registrar_apoio(demanda, "98922223333")
    demanda.avancar_status(operador)
    resp = cliente_logado.get(reverse("indicadores"))
    assert resp.status_code == 200
    ctx = resp.context
    assert ctx["total"] == 1 and ctx["afetados"] == 2 and ctx["apoios"] == 1
    assert ctx["levadas"] == 1 and ctx["pct_levadas"] == 100 and ctx["resolvidas"] == 0
    assert ctx["dias_ate_prefeitura"] is not None
    assert "Esgoto a céu aberto" in resp.text and "Cláudia" not in resp.text


def test_indicadores_sem_demandas(cliente_logado):
    resp = cliente_logado.get(reverse("indicadores"))
    assert resp.context["total"] == 0 and resp.context["dias_ate_prefeitura"] is None
    assert "Ainda não há demandas" in resp.text
