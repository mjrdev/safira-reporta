"""Testes de integração do fluxo do morador: registrar, apoiar e consultar (RF01, RF02, RF06, RF08)."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from reports.models import Apoio, Demanda

from .conftest import gerar_imagem

pytestmark = pytest.mark.django_db


def dados_registro(categoria, **extra):
    dados = {
        "categoria": categoria.pk,
        "foto": SimpleUploadedFile("rua.jpg", gerar_imagem(), content_type="image/jpeg"),
        "latitude": "-2.530000",
        "longitude": "-44.150000",
        "ponto_referencia": "Rua Fictícia A",
        "descricao": "Esgoto correndo na frente da casa 40.",
        "nome_morador": "Cláudia",
        "telefone_morador": "(98) 90000-0000",
    }
    dados.update(extra)
    return dados


def test_home_abre_sem_login_e_mostra_acoes(client):
    resp = client.get(reverse("home"))
    assert resp.status_code == 200
    assert "Registrar problema" in resp.text and "Consultar meu protocolo" in resp.text


def test_registro_completo_gera_protocolo_e_mostra_confirmacao(client, esgoto):
    resp = client.post(reverse("registrar"), dados_registro(esgoto), follow=True)
    demanda = Demanda.objects.get()
    assert resp.status_code == 200
    assert demanda.protocolo in resp.text
    assert "Problema registrado" in resp.text
    assert demanda.telefone_morador == "98900000000"
    assert demanda.status == Demanda.Status.RECEBIDO


def test_registro_sem_categoria_mostra_erro_no_campo(client, esgoto):
    dados = dados_registro(esgoto)
    dados.pop("categoria")
    resp = client.post(reverse("registrar"), dados)
    assert resp.status_code == 200
    assert "Escolha uma categoria para continuar." in resp.text
    assert Demanda.objects.count() == 0


def test_registro_com_arquivo_que_nao_e_imagem_e_recusado(client, esgoto):
    falso = SimpleUploadedFile("shell.jpg", b"<?php echo 1; ?>", content_type="image/jpeg")
    resp = client.post(reverse("registrar"), dados_registro(esgoto, foto=falso))
    assert "A foto precisa ser JPG ou PNG" in resp.text
    assert Demanda.objects.count() == 0


def test_registro_sem_gps_e_sem_referencia_e_recusado(client, esgoto):
    resp = client.post(reverse("registrar"), dados_registro(esgoto, latitude="", longitude="", ponto_referencia=""))
    assert "Use sua localização ou escreva a rua" in resp.text
    assert Demanda.objects.count() == 0


def test_registro_com_telefone_incompleto_e_recusado(client, esgoto):
    resp = client.post(reverse("registrar"), dados_registro(esgoto, telefone_morador="(98) 9000"))
    assert "Telefone incompleto" in resp.text


def test_registro_perto_de_demanda_existente_oferece_apoio(client, demanda, esgoto):
    resp = client.post(reverse("registrar"), dados_registro(esgoto, latitude="-2.530300", longitude="-44.150200"))
    assert "Já registraram este problema aqui perto" in resp.text
    assert "também sou afetado" in resp.text
    assert Demanda.objects.count() == 1


def test_morador_pode_confirmar_que_e_outro_problema(client, demanda, esgoto):
    dados = dados_registro(esgoto, latitude="-2.530300", longitude="-44.150200", confirmar_novo="1")
    client.post(reverse("registrar"), dados)
    assert Demanda.objects.count() == 2


def test_apoio_soma_afetados_e_nao_duplica(client, demanda):
    url = reverse("apoiar", args=[demanda.protocolo])
    client.post(url, {"telefone": "98922223333"})
    client.post(url, {"telefone": "(98) 92222-3333"})
    demanda.refresh_from_db()
    assert demanda.total_afetados == 2
    assert Apoio.objects.count() == 1
    assert "98922223333" not in Apoio.objects.get().telefone_hash


def test_consulta_por_protocolo_mostra_status_sem_dados_pessoais(client, demanda):
    resp = client.get(reverse("consultar"), {"protocolo": demanda.protocolo.lower()}, follow=True)
    assert resp.status_code == 200
    assert "Recebido" in resp.text and demanda.protocolo in resp.text
    assert "Cláudia" not in resp.text and "98900000000" not in resp.text


def test_consulta_protocolo_inexistente(client, db):
    resp = client.get(reverse("consulta_protocolo", args=["SAF-2026-9999"]))
    assert resp.status_code == 404
    assert "Protocolo não encontrado" in resp.text


def test_consulta_com_formato_invalido_ou_sql_injection_nao_retorna_dados(client, demanda):
    resp = client.get(reverse("consultar"), {"protocolo": "' OR 1=1 --"})
    assert resp.status_code == 200
    assert "O protocolo tem o formato" in resp.text
    assert demanda.protocolo not in resp.text


def test_consulta_tem_limite_por_ip(client, settings, db):
    settings.CONSULTA_MAX_POR_MINUTO = 3
    for _ in range(3):
        client.get(reverse("consultar"))
    assert client.get(reverse("consultar")).status_code == 429


def test_descricao_com_script_e_exibida_escapada(cliente_logado, client, esgoto):
    client.post(reverse("registrar"), dados_registro(esgoto, descricao="<script>alert(1)</script>"))
    d = Demanda.objects.get()
    resp = cliente_logado.get(reverse("detalhe", args=[d.protocolo]))
    assert "<script>alert(1)</script>" not in resp.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in resp.text


def test_pagina_de_resolvidos_lista_so_resolvidos_sem_dados_pessoais(client, demanda, operador):
    assert "Ainda não há problemas" in client.get(reverse("resolvidos")).text
    demanda.avancar_status(operador)
    demanda.avancar_status(operador)
    resp = client.get(reverse("resolvidos"))
    assert "Esgoto a céu aberto" in resp.text
    assert "Cláudia" not in resp.text


def test_tela_de_registro_tem_indicadores_de_carregamento_acessiveis(client, db):
    resp = client.get(reverse("registrar"))
    assert resp.status_code == 200
    assert 'id="status-foto"' in resp.text
    assert 'id="status-envio"' in resp.text
    assert resp.text.count('role="status" aria-live="polite"') >= 2
    assert 'id="botao-enviar" data-texto-enviando="Enviando a foto, aguarde…"' in resp.text


def test_respostas_tem_content_security_policy(client, db):
    resp = client.get(reverse("home"))
    assert "default-src 'self'" in resp["Content-Security-Policy"]
