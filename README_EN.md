# Health Information Assistant — Marília, Brazil

**Language:** [English](README_EN.md) | [Português](README.md)

[![CI](https://github.com/FelipeStv0/ubs-marilia-rag-assistant_n8n_automation/actions/workflows/ci.yml/badge.svg)](https://github.com/FelipeStv0/ubs-marilia-rag-assistant_n8n_automation/actions/workflows/ci.yml)

An independent prototype that helps people find **administrative information** about public health centers (UBS and USF) in Marília, São Paulo, Brazil. It collects content from approved official websites, stores document versions, and shows source references with search results.

> **Current status: testing — no paid AI service or active LLM.** The default system uses **lexical search and extracts text** from registered sources. It does not generate new answers with a language model. The Python API is active; only the external AI service is disabled. Optional embeddings and LLM features exist but are not required.

> **Important:** This project is not connected to the City of Marília or its Health Department. It does not provide medical advice, diagnosis, triage, appointments, or real-time vaccine availability. Always confirm important information with the health center.

## Main features

- Scheduled collection from **approved URLs** listed in `sources.json`, using n8n.
- HTML text extraction, document splitting, and SHA-256 change detection.
- PostgreSQL document history: old versions are kept, but only active versions are searched.
- Portuguese text search, lexical similarity, and stricter matching for named health centers.
- Original text snippets, source links, and the last successful collection time.
- Two separate n8n workflows: one for source updates and one for questions.
- Optional LLM and vector search integrations, disabled in the current default setup.
- Local web interface, Nginx proxy, API validation, automated tests, and GitHub Actions.

## Technology stack

| Component | Technology | Purpose |
| --- | --- | --- |
| Automation | n8n 2.x | Schedules, webhooks, and HTTP workflows |
| Backend | Python, FastAPI, Pydantic | Endpoints and application rules |
| Data collection | Requests, Beautiful Soup | Download and process HTML |
| Database | PostgreSQL 16 | Sources, text passages, versions, and search |
| Optional vector search | pgvector | Store and search embeddings when enabled |
| Frontend | HTML, CSS, JavaScript | Browser interface |
| Web server | Nginx | Static files, reverse proxy, and request limits |
| Infrastructure | Docker Compose | Local services and networks |
| Quality | pytest, GitHub Actions | Automated checks and integration tests |

## How it works

~~~mermaid
flowchart TD
    S[Approved public sources] --> C[n8n Workflow 01: scheduled collection]
    C --> A[FastAPI: text processing and versioning]
    A <--> D[(PostgreSQL + optional pgvector)]
    U[User] --> W[Web interface / Nginx]
    W --> Q[n8n Workflow 02: questions]
    Q --> R[FastAPI: search and response]
    R <--> D
    R --> Q
    Q --> W
~~~

The question workflow searches content already stored in the database. It **does not open arbitrary URLs supplied by users**. Collection and question handling are independent.

## Run locally on Windows

**Requirements:** Docker Desktop with WSL 2 and Python 3.11 or newer.

The documented setup uses **two Docker Compose projects**: the main project for PostgreSQL, FastAPI, and Nginx, and a separate private Compose project for the migrated n8n instance. The n8n editor runs at `http://localhost:5679`; the web interface runs at `http://localhost:8080`.

**For an existing installation, keep the private `.env` files and persistent volumes unchanged. Do not run `docker compose down -v`.** The main database and the migrated n8n instance use separate private secrets.

From the repository root, with the migrated n8n private Compose file already configured:

~~~powershell
$pasta = "$HOME\Documents\UBS-Backup\migracao-n8n"
docker compose up -d --build db api
docker compose -f "$pasta\compose.yaml" up -d
docker compose up -d web
docker compose ps
python scripts/validar_execucao.py
~~~

The safe startup script for an existing Windows setup is:

~~~powershell
powershell -ExecutionPolicy Bypass -File .\scripts\iniciar_windows.ps1
~~~

For a **new** installation, read [the migration/setup guide](docs/MIGRACAO_N8N.md) before creating environment files or volumes. The repository includes a template without secrets at `deploy/n8n-migrado.compose.yaml`. Import and publish the two workflows in the migrated n8n instance; updating JSON files in Git does not automatically update imported workflows.

The main Compose project **does not start the old n8n instance**. The old instance and its backups must be handled separately.

## Verify the system

~~~powershell
python -m pip install -r api/requirements-dev.txt
python -m pytest -q tests/
python -m compileall -q api/app scripts
docker compose config
~~~

GitHub Actions runs unit tests, workflow contract checks, security-related file checks, and **FastAPI integration tests with PostgreSQL/pgvector**. These tests do not prove that the user's local n8n instance, Nginx, or scheduled collection is currently running.

For a full local check, start the services and run:

~~~powershell
python scripts/validar_execucao.py
~~~

Optional collection through the backend:

~~~powershell
python scripts/validar_execucao.py --coletar
~~~

The script saves detailed reports under `artifacts/`, which is excluded from Git. Failed cases remain marked as failures. Collection through the backend **does not prove** that n8n Workflow 01 ran successfully.

## Documented tests and limitations

- **November 8, 2026:** a local audit reported six sources, 92 active passages, and no source collection errors. Four technical scenarios initially passed, but a manual review found **one relevance issue**: an address question returned opening hours. The response rules were corrected to require address evidence.
- **November 9, 2026:** the migrated n8n instance processed six sources with no collection failures. Four question scenarios passed through Nginx after the older n8n instance was stopped.
- The address correction and any later changes still require a new end-to-end check in the local environment before claiming full operational validation.

Read the [answer audit](docs/AUDITORIA_RESPOSTAS_REAIS_2026-11-08.md), [execution evidence](docs/EVIDENCIAS_EXECUCAO_2026-11-08.md), and [reproduction guide](docs/DEMONSTRACAO.md) for details.

**Current limitations:** lexical similarity does not guarantee that a source is correct or up to date. Different official pages may disagree. A missing result does not mean a service is unavailable. Collection time is not the same as publication date or validity date. No clinical interpretation is provided.

## Project structure

| Path | Responsibility |
| --- | --- |
| `api/app/main.py` | FastAPI routes and request validation |
| `api/app/collector.py` and `text_processing.py` | Collection, HTML processing, and passages |
| `api/app/rag.py` and `query_policy.py` | Search, question rules, and source evidence |
| `api/app/llm.py` | Optional LLM-related integration |
| `db/init.sql` | Database structure and indexes |
| `workflows/` | n8n collection and question workflows |
| `web/` and `nginx/` | Browser interface and reverse proxy |
| `scripts/` | Startup, checks, and local reports |
| `tests/` | Unit, contract, and database integration tests |

For changes or new integrations, see the [maintenance guide](docs/GUIA_MANUTENCAO.md), [architecture decisions](docs/ARQUITETURA.md), and [operations guide](docs/OPERACAO.md). **Detailed supporting guides are currently in Portuguese.**

## Security and data use

- Do not enter personal health information or patient records.
- Do not commit credentials, private `.env` files, database backups, or real patient data.
- The supplied deployment is intended for **local access**, not a public internet service.
- Adding new source domains requires a review of their legitimacy and access rules.
- A previous n8n encryption key was potentially exposed. Do not replace encryption keys directly in existing data volumes; follow the [credential safety guide](docs/SEGURANCA_CREDENCIAIS.md).
- Production use would need access control, HTTPS, monitoring, privacy review, and institutional approval.

## Possible next steps

Improve source freshness checks, build a labeled set of questions to measure retrieval quality, add source monitoring, and consider LLM support **only after cost and privacy approval**.

---

**Project type:** independent technical prototype for learning and portfolio demonstration. It is not a medical service or an official public health communication.
