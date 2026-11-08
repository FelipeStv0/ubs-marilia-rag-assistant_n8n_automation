"""Regression cases from local evidence; no network or real patient data."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from app import rag
from validar_execucao import evaluate, semantic_check


def passage(body):
    return {
        "id": 42, "body": body, "title": "Fonte de teste",
        "url": "https://www.marilia.sp.gov.br/exemplo", "priority": 90,
        "published_at": None, "last_success_at": None,
        "status": "ok", "last_checked_at": None,
    }


def test_location_question_rejects_hours_only():
    text = "UBS Castelo Branco: atendimento até as 22h de segunda a sexta-feira."
    with patch.object(rag, "openai_key", return_value=""), patch.object(
        rag, "_retrieve", return_value=[passage(text)]
    ):
        result = rag.answer("Onde fica a UBS Castelo Branco?")
    assert result["mode"] == "no_evidence"
    assert result["sources"] == []
    assert result["sufficient"] is False


def test_location_question_prefers_passage_with_nearby_street():
    bad = passage("UBS Castelo Branco: atendimento até as 22h.")
    good = passage("UBS Castelo Branco\nRua Exemplo, 123\nAtendimento: consultar a unidade.")
    with patch.object(rag, "openai_key", return_value=""), patch.object(
        rag, "_retrieve", return_value=[bad, good]
    ):
        result = rag.answer("Onde fica a UBS Castelo Branco?")
    assert result["mode"] == "extractive"
    assert good["body"] in result["answer"]
    assert bad["body"] not in result["answer"]


def test_semantic_smoke_rejects_original_hours_response():
    ok, reason = semantic_check("endereco_ubs", "UBS Castelo Branco atende até as 22h.")
    assert not ok
    assert "logradouro" in reason


def test_semantic_smoke_accepts_street_and_vaccine_documents():
    assert semantic_check("endereco_ubs", "UBS Castelo Branco — Rua Exemplo, 123")[0]
    assert semantic_check("documentos_vacina", "Levar carteira de vacinação e CPF")[0]


def test_evaluator_reports_failure_when_http_success_but_semantics_wrong():
    response = {
        "http_status": 200, "latency_ms": 10,
        "data": {
            "mode": "extractive", "sufficient": True,
            "answer": "Modo de testes — sem API de IA. UBS Castelo Branco atende até as 22h.",
            "sources": [{"title": "Fonte de teste",
                        "url": "https://www.marilia.sp.gov.br/exemplo",
                        "excerpt": "UBS Castelo Branco atende até as 22h.",
                        "checked_at": "2026-11-08T21:00:00+00:00"}],
        },
    }
    with patch("validar_execucao.call", return_value=response):
        result = evaluate("http://127.0.0.1:8080", (
            "endereco_ubs", "Onde fica a UBS Castelo Branco?", "extractive", True
        ))
    assert result["http_status"] == 200
    assert result["result"] == "FALHOU"
    assert result["semantic_ok"] is False
