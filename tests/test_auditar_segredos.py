"""Testes do auditor sem acesso a credenciais reais nem ao Docker."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from auditar_segredos import evaluate, parse_env, sensitive_tracked_paths, audit


def test_parse_env_without_exposing_values():
    env = parse_env("POSTGRES_PASSWORD='secret123'\nN8N_ENCRYPTION_KEY=\"abcdefgh\"\n# comment\n")
    assert env["POSTGRES_PASSWORD"] == "secret123"
    assert env["N8N_ENCRYPTION_KEY"] == "abcdefgh"


def test_evaluation_never_echoes_secret():
    secret = "s3cr3tPRIVATEstringDoNotPrint1234567890"
    results = evaluate({"POSTGRES_PASSWORD": secret, "N8N_ENCRYPTION_KEY": secret,
                        "OPENAI_API_KEY": ""})
    assert all(secret not in description for _, description in results)
    assert all(level == "OK" for level, _ in results)


def test_placeholder_and_short_secret_fail():
    results = evaluate({"POSTGRES_PASSWORD": "short", "N8N_ENCRYPTION_KEY":
                        "SUBSTITUIR_POR_CHAVE_DE_32_OU_MAIS_CARACTERES"})
    assert sum(level == "FAIL" for level, _ in results) == 2


def test_warn_when_llm_enabled_unexpectedly():
    result = evaluate({"POSTGRES_PASSWORD": "x" * 40,
                       "N8N_ENCRYPTION_KEY": "y" * 40, "OPENAI_API_KEY": "hidden"})
    assert any(level == "WARN" for level, _ in result)
    assert not any("hidden" in description for _, description in result)


def test_tracked_paths_detection():
    hits = sensitive_tracked_paths([
        "README.md", ".env", ".env.production", ".env.example", "certs/private.pem",
        "artifacts/execucao-real.json", "docs/OPERACAO.md", "n8n_data/config"])
    assert len(hits) == 5
    assert ".env.example" not in hits


def test_audit_missing_env_does_not_generate_secret(tmp_path):
    (tmp_path / ".gitignore").write_text(".env\n.env.*\nartifacts/\n*.key\n*.pem\n",
                                           encoding="utf-8")
    result = audit(tmp_path)
    assert any(level == "FAIL" for level, _ in result)
    assert not (tmp_path / ".env").exists()
