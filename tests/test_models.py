"""Testes unitários das regras de negócio dos models (RF01, RF04)."""

import pytest
from django.core.exceptions import ValidationError

from reports.models import Demanda, HistoricoStatus

pytestmark = pytest.mark.django_db


def test_categorias_iniciais_criadas_pela_migration():
    from reports.models import Categoria

    nomes = set(Categoria.objects.values_list("nome", flat=True))
    assert {"Esgoto a céu aberto", "Água parada", "Falta de água", "Buraco", "Barro"} <= nomes


def test_protocolo_gerado_no_formato_e_sequencial(demanda, esgoto, foto_jpg):
    ano = demanda.criado_em.year
    assert demanda.protocolo == f"SAF-{ano}-0001"
    outra = Demanda.objects.create(
        categoria=esgoto,
        descricao="x",
        foto=foto_jpg,
        ponto_referencia="Rua B",
        nome_morador="Ana",
        telefone_morador="98911111111",
    )
    assert outra.protocolo == f"SAF-{ano}-0002"


def test_nova_demanda_comeca_recebida_com_historico(demanda):
    assert demanda.status == Demanda.Status.RECEBIDO
    assert demanda.historico.count() == 1
    assert demanda.historico.first().status_novo == Demanda.Status.RECEBIDO


def test_status_avanca_na_ordem_e_registra_historico(demanda, operador):
    demanda.avancar_status(operador, "entregue no relatório")
    assert demanda.status == Demanda.Status.LEVADO
    demanda.avancar_status(operador)
    assert demanda.status == Demanda.Status.RESOLVIDO
    historico = list(demanda.historico.values_list("status_novo", flat=True))
    assert historico == ["recebido", "levado_prefeitura", "resolvido"]
    assert demanda.historico.last().alterado_por == operador


def test_demanda_resolvida_nao_avanca_mais(demanda, operador):
    demanda.avancar_status(operador)
    demanda.avancar_status(operador)
    with pytest.raises(ValidationError):
        demanda.avancar_status(operador)


def test_historico_nao_pode_ser_editado_nem_apagado(demanda):
    h = HistoricoStatus.objects.first()
    h.observacao = "alterado"
    with pytest.raises(ValidationError):
        h.save()
    with pytest.raises(ValidationError):
        h.delete()


def test_demanda_sem_gps_exige_ponto_de_referencia(esgoto, foto_jpg):
    d = Demanda(categoria=esgoto, descricao="x", foto=foto_jpg, nome_morador="A", telefone_morador="98911111111")
    with pytest.raises(ValidationError):
        d.clean()
