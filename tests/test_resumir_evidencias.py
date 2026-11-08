"""Sanitizer tests: no private answer, keys or copied excerpts in public summary."""
import copy
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from resumir_evidencias import summarize


def example():
    def case(name, mode, sources=None):
        return {"case": name, "http_status": 200, "mode": mode,
                "result": "PASSOU", "question": "PRIVATE_QUESTION",
                "answer": "PRIVATE_ANSWER", "sources": sources or []}
    return {
        "mode": "extractive_lexical", "result": "PASSOU",
        "date_utc": "2026-11-08T16:00:00+00:00",
        "cases": [
            case("endereco_ubs", "extractive", [{"url": "https://www.marilia.sp.gov.br/portal/",
                  "excerpt": "PRIVATE_EXCERPT", "title": "Fonte"}]),
            case("documentos_vacina", "extractive"),
            case("unidade_inexistente", "no_evidence"),
            case("emergencia", "safety"),
        ],
        "status": {"http_status": 200, "result": "PASSOU"},
        "blocked_method": {"http_status": 403, "result": "PASSOU"},
    }


def test_public_summary_omits_sensitive_response_content():
    report = example()
    text = summarize(report)
    assert "endereco_ubs" in text and "extractive_lexical" not in text
    for secret in ("PRIVATE_QUESTION", "PRIVATE_ANSWER", "PRIVATE_EXCERPT",
                   "https://www.marilia.sp.gov.br/portal/"):
        assert secret not in text


def test_missing_case_rejected():
    report = example()
    report["cases"] = report["cases"][:-1]
    with pytest.raises(ValueError):
        summarize(report)


def test_wrong_mode_rejected():
    report = example()
    report["mode"] = "llm_and_vector"
    with pytest.raises(ValueError):
        summarize(report)


def test_foreign_source_rejected():
    report = example()
    report["cases"][0]["sources"][0]["url"] = "https://not-allowed.example/path"
    with pytest.raises(ValueError):
        summarize(report)


def test_inconsistent_aggregate_rejected():
    report = example()
    report["cases"][0]["result"] = "FALHOU"
    with pytest.raises(ValueError):
        summarize(report)
