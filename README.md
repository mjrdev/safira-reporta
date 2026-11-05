# Safira Reporta

Sistema web para os moradores do bairro **Safira (Paço do Lumiar – MA)** registrarem problemas de
saneamento e pavimentação com foto e localização, e para a **Associação de Moradores do Safira**
organizar essas demandas e levá-las à prefeitura em um relatório documentado.

Projeto da disciplina de Projeto de Software (Experiências Práticas I, II e III). ODS 6, meta 6.b.

## Funcionalidades

| Requisito | Descrição | Onde |
|---|---|---|
| RF01 | Registrar problema com categoria, foto, localização e protocolo | `/registrar/` |
| RF02 | Consultar situação pelo protocolo (sem dados pessoais) | `/consultar/` |
| RF03 | Painel da associação com lista e filtros | `/painel/` |
| RF04 | Avançar status com histórico (Recebido → Levado à prefeitura → Resolvido) | `/painel/demanda/<protocolo>/` |
| RF05 | Relatório imprimível/PDF para a prefeitura | `/painel/relatorio/` |
| RF06 | “Também sou afetado”: apoio a demanda próxima (até 100 m) sem duplicar | registro e consulta |
| RF07 | Mapa das demandas no painel (Leaflet + OpenStreetMap) | `/painel/` |
| RF08 | Página pública de problemas resolvidos | `/resolvidos/` |

Segurança (RNF01/RNF02): senhas com Argon2id, sessão com cookies seguros, limite de tentativas de login
e de consultas, CSRF, CSP, ORM (consultas parametrizadas), escape automático nos templates, validação e
regravação das fotos sem EXIF, telefone dos apoios guardado só como HMAC.

## Arquitetura

Monolito Django em camadas (Model–View–Template):

```
config/            configurações (tudo sensível via variáveis de ambiente)
reports/models.py  Categoria, Demanda, Apoio, HistoricoStatus + regras de status/protocolo
reports/services.py telefone, proximidade, apoio e processamento de foto
reports/forms.py   validação no servidor
reports/views.py   fluxo do morador e painel da associação
reports/templates/ telas mobile-first e acessíveis
tests/             testes unitários e de integração (pytest-django)
```

## Rodando localmente

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # ajuste as variáveis
export $(grep -v '^#' .env | xargs)
python manage.py migrate        # cria tabelas e as 5 categorias
python manage.py createsuperuser
DEBUG=1 python manage.py runserver
```

Com Docker: `docker compose up --build` (sobe PostgreSQL 16 + aplicação).

## Testes

```bash
pytest --cov --cov-report=term-missing
ruff check . && ruff format --check .
```

## Integração contínua

O workflow `.github/workflows/ci.yml` roda em todo push e Pull Request: lint (ruff), checagem de
migrations, testes com PostgreSQL e cobertura mínima de 85%, `check --deploy`, `pip-audit` e build da
imagem Docker.

## Fluxo de trabalho

- `main` protegida; cada mudança entra por branch `feat/…`, `fix/…`, `test/…` ou `ci/…` e Pull Request.
- Commits no padrão Conventional Commits (`feat:`, `fix:`, `test:`, `ci:`, `docs:`, `chore:`).
- O PR só é mesclado com a CI verde e o checklist de auto-revisão preenchido.
