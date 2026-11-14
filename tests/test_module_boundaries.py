"""Testes das fronteiras entre política de consulta e mecanismo de resposta."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import query_policy, rag
from app import collector, text_processing


def test_api_legacy_usa_mesmas_funcoes():
    assert rag.keywords is query_policy.keywords
    assert rag.location_supported is query_policy.location_supported
    assert collector.extract_text is text_processing.extract_text
    assert collector.split_chunks is text_processing.split_chunks


def test_endereco_nao_e_inferido_de_horario():
    pergunta = "Qual o endereço da UBS Castelo Branco?"
    assert query_policy.location_requested(pergunta)
    assert not query_policy.location_supported(
        pergunta, {"body": "UBS Castelo Branco. Horário: 7h às 17h."}
    )
    assert query_policy.location_supported(
        pergunta, {"body": "UBS Castelo Branco. Rua Exemplo, 10."}
    )
