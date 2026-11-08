"""Integration against actual FastAPI + PostgreSQL, not n8n or live websites.

Synthetic passages must never be presented as official Marilia information.
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api"))
from app import collector
from app.db import connect
from app.main import app

pytestmark = pytest.mark.skipif(os.getenv("RUN_INTEGRATION_TESTS") != "1",
                                reason="Requires PostgreSQL and RUN_INTEGRATION_TESTS=1")
SOURCE = {
    "id": "fixture_laboratorio", "title": "FONTE SINTETICA DE TESTE (NAO OFICIAL)",
    "url": "https://www.marilia.sp.gov.br/portal/secretarias-paginas/16/unidades-de-saude---marilia-e-regiao/",
    "category": "unidades", "priority": 80, "published_at": None,
}
BODY = (
    "UBS LABORATORIO TESTES\n"
    "Endereco simulado: Rua Exemplo, 123. Dado sintetico; nao descreve unidade real.\n"
    "Atendimento simulado: consulte a unidade. Este trecho e usado apenas no teste."
)


@pytest.fixture(autouse=True)
def seed_db(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    with connect() as conn:
        conn.execute("TRUNCATE ubs.ingestion_runs, ubs.passages, ubs.sources RESTART IDENTITY CASCADE")
        conn.execute(
            """INSERT INTO ubs.sources
               (source_id,url,title,category,priority,status,last_checked_at,last_success_at,chunk_count)
               VALUES (%s,%s,%s,%s,%s,'ok',now(),now(),1)""",
            (SOURCE["id"], SOURCE["url"], SOURCE["title"], SOURCE["category"], 80),
        )
        conn.execute(
            """INSERT INTO ubs.passages (source_id,revision_hash,chunk_index,body,active)
               VALUES (%s,'fixture1',0,%s,TRUE)""",
            (SOURCE["id"], BODY),
        )
    yield


def test_health_and_status_with_real_postgres():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"ok": True}
        result = client.get("/internal/status")
    assert result.status_code == 200
    assert result.json()["sources_ok"] == 1
    assert result.json()["passages"] == 1
    assert result.json()["rag_mode"] == "extractive_lexical"


def test_extractive_question_and_real_database_record():
    with TestClient(app) as client:
        result = client.post("/internal/answer", json={
            "question": "Onde fica a UBS Laboratorio Testes?"
        })
    assert result.status_code == 200
    data = result.json()
    assert data["mode"] == "extractive"
    assert data["sufficient"] is True
    assert BODY in data["answer"]
    assert data["sources"][0]["url"] == SOURCE["url"]
    assert data["sources"][0]["checked_at"]
    assert data["sources"][0]["source_status"] == "ok"


def test_no_evidence_validation_and_safety():
    with TestClient(app) as client:
        missing = client.post("/internal/answer", json={
            "question": "Qual o endereco da UBS Inexistente Arco Iris 999?"
        })
        invalid = client.post("/internal/answer", json={"question": "Oi"})
        urgent = client.post("/internal/answer", json={"question": "Estou com dor no peito"})
    assert missing.status_code == 200 and missing.json()["mode"] == "no_evidence"
    assert missing.json()["sources"] == []
    assert invalid.status_code == 422
    assert urgent.status_code == 200 and urgent.json()["mode"] == "safety"
    assert urgent.json()["sources"] == []


def test_ingestion_failure_retains_prior_passage_and_flags_stale_data():
    with patch.object(collector, "_safe_get", side_effect=requests.Timeout("falha simulada")):
        with connect() as conn:
            result = collector.ingest_one(conn, SOURCE)
    assert result["status"] == "failed"
    with connect() as conn:
        status = conn.execute(
            "SELECT status,last_success_at FROM ubs.sources WHERE source_id=%s",
            (SOURCE["id"],),
        ).fetchone()
        count = conn.execute(
            "SELECT COUNT(*) AS total FROM ubs.passages WHERE source_id=%s AND active",
            (SOURCE["id"],),
        ).fetchone()["total"]
    assert status["status"] == "error" and status["last_success_at"] is not None and count == 1
    with TestClient(app) as client:
        answer = client.post("/internal/answer", json={
            "question": "Onde fica a UBS Laboratorio Testes?"
        })
    assert answer.status_code == 200
    assert answer.json()["sources"][0]["source_status"] == "error"
