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
| RF09 | Indicadores de uso e impacto para a associação | `/painel/indicadores/` |

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

## Publicação (Render) e monitoramento

O arquivo `render.yaml` cria no [Render](https://render.com) o banco PostgreSQL e o serviço web:

1. No Render: **New → Blueprint** e escolha este repositório.
2. Preencha as variáveis marcadas como `sync: false` (usuário inicial do painel e, se quiser, `SENTRY_DSN` e o bucket de fotos).
3. Cada push na `main` com a CI verde gera um novo deploy (`autoDeploy`).

O `migrate` e a criação do usuário inicial rodam no início do `startCommand`, e não no build: durante o build o Render não dá acesso à rede privada onde fica o banco, e o plano free não tem `preDeployCommand`.

Monitoramento pós-lançamento:

- `GET /saude/` responde `{"status": "ok", "banco": "ok"}` (ou HTTP 503 se o banco cair). É o health check do Render e o endereço vigiado pelo UptimeRobot a cada 5 minutos.
- Erros da aplicação vão para o Sentry quando `SENTRY_DSN` está definido, sem dados pessoais (`send_default_pii=False`).
- Logs de acesso do gunicorn ficam na aba **Logs** do Render.

No plano gratuito o disco é apagado a cada deploy. Para as fotos não se perderem, configure o Supabase Storage nas variáveis `AWS_*`.

## Integração contínua

O workflow `.github/workflows/ci.yml` roda em todo push e Pull Request: lint (ruff), checagem de
migrations, testes com PostgreSQL e cobertura mínima de 85%, `check --deploy`, `pip-audit` e build da
imagem Docker.

## Fluxo de trabalho

- `main` protegida; cada mudança entra por branch `feat/…`, `fix/…`, `test/…` ou `ci/…` e Pull Request.
- Commits no padrão Conventional Commits (`feat:`, `fix:`, `test:`, `ci:`, `docs:`, `chore:`).
- O PR só é mesclado com a CI verde e o checklist de auto-revisão preenchido.
