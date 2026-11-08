import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from app import rag


def passage(text):
    return {
        "id": 42, "body": text, "title": "Fonte oficial",
        "url": "https://www.marilia.sp.gov.br/exemplo",
        "published_at": None, "last_success_at": None,
        "priority": 80,
    }


def test_extractive_mode_never_invents_details():
    body = "UBS NOVA MARILIA\nAtendimento: consultar a unidade.\nRua Exemplo."
    with patch.object(rag, "openai_key", return_value=""), patch.object(rag, "_retrieve", return_value=[passage(body)]):
        result = rag.answer("Onde fica a UBS Nova Marília?")
    assert result["mode"] == "extractive"
    assert body in result["answer"]
    assert "sem API de IA" in result["answer"]
    assert result["sources"][0]["url"].startswith("https://")


def test_no_evidence_abstains():
    with patch.object(rag, "openai_key", return_value=""), patch.object(rag, "_retrieve", return_value=[]):
        result = rag.answer("Qual horário de uma unidade inexistente?")
    assert result["mode"] == "no_evidence"
    assert result["sufficient"] is False
    assert result["sources"] == []


def test_emergency_does_not_claim_fetched_source():
    result = rag.answer("Estou com dor no peito")
    assert result["mode"] == "safety"
    assert result["sources"] == []
    assert "192" in result["answer"]
