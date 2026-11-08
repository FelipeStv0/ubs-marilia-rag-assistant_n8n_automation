"""Auditoria local, somente leitura, de higiene de segredos.

Nunca imprime valores do .env, chaves ou saidas de 'docker compose config'.
Nao modifica o ambiente ou reinicia containers.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SENSITIVE_NAMES = {".env", "id_rsa", "id_ed25519"}
RISKY_SUFFIXES = (".pem", ".p12", ".pfx", ".key")
PLACEHOLDERS = ("SUBSTITUIR_", "CHANGE_ME", "CHANGEME", "YOUR_", "EXAMPLE_", "INSIRA_")
MIN_SECRET_LENGTH = 32


def parse_env(content: str) -> dict[str, str]:
    result = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        result[key] = value
    return result


def evaluate(values: dict[str, str], *, require_no_llm: bool = True) -> list[tuple[str, str]]:
    """Retorna (nivel, descricao); jamais inclui valores de configuracao."""
    findings = []
    for key in ("POSTGRES_PASSWORD", "N8N_ENCRYPTION_KEY"):
        value = values.get(key, "")
        if not value:
            findings.append(("FAIL", key + " ausente ou vazio"))
        elif len(value) < MIN_SECRET_LENGTH or value.upper().startswith(PLACEHOLDERS):
            findings.append(("FAIL", key + " parece fraco ou placeholder"))
        else:
            findings.append(("OK", key + " definido (valor oculto)"))
    if require_no_llm:
        if values.get("OPENAI_API_KEY", "").strip():
            findings.append(("WARN", "OPENAI_API_KEY preenchida; modo sem LLM nao garantido"))
        else:
            findings.append(("OK", "OPENAI_API_KEY vazia (sem LLM paga)"))
    return findings


def sensitive_tracked_paths(paths: list[str]) -> list[str]:
    hits = []
    for raw in paths:
        path = raw.replace("\\", "/")
        name = path.rsplit("/", 1)[-1].lower()
        if (name in SENSITIVE_NAMES or name.startswith(".env.")
                and name != ".env.example"
                or name.endswith(RISKY_SUFFIXES)
                or path.startswith("artifacts/")
                or path.startswith("n8n_data/")
                or path.startswith("data/")):
            hits.append(path)
    return hits


def check_git(root: Path) -> list[tuple[str, str]]:
    if not (root / ".git").exists():
        return [("INFO", "Sem metadados Git locais; nao e possivel verificar arquivos rastreados no ZIP")]
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True, check=True, timeout=12,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return [("WARN", "Nao foi possivel consultar arquivos rastreados no Git")]
    paths = [x.decode("utf-8", errors="replace") for x in proc.stdout.split(b"\0") if x]
    sensitive = sensitive_tracked_paths(paths)
    if sensitive:
        # Nao mostrar caminhos potencialmente sensiveis no terminal publico.
        return [("FAIL", "Arquivos de risco rastreados pelo Git: " + str(len(sensitive)))]
    return [("OK", "Nenhum caminho sensivel rastreado pelo Git")]


def check_layout(root: Path) -> list[tuple[str, str]]:
    findings = []
    ignore = (root / ".gitignore")
    if not ignore.exists():
        findings.append(("FAIL", "Arquivo .gitignore ausente"))
    else:
        entries = {x.strip() for x in ignore.read_text(encoding="utf-8").splitlines()}
        for required in (".env", ".env.*", "artifacts/", "*.key", "*.pem"):
            if required not in entries:
                findings.append(("WARN", "Ausencia de padrao de protecao no .gitignore: " + required))
    compose = root / "docker-compose.yml"
    if compose.exists():
        config = compose.read_text(encoding="utf-8")
        for bind in ("127.0.0.1:5678:5678", "127.0.0.1:8080:80"):
            if bind not in config:
                findings.append(("WARN", "Binding local nao identificado em docker-compose.yml"))
    return findings


def audit(root: Path, require_no_llm: bool = True) -> list[tuple[str, str]]:
    findings = []
    path = root / ".env"
    if not path.exists():
        findings.append(("FAIL", ".env nao encontrado na pasta do projeto"))
    else:
        try:
            content = path.read_text(encoding="utf-8")
            findings.extend(evaluate(parse_env(content), require_no_llm=require_no_llm))
        except OSError:
            findings.append(("FAIL", "Nao foi possivel ler o .env"))
    findings.extend(check_layout(root))
    findings.extend(check_git(root))
    findings.append(("INFO", "A auditoria nao verifica se chaves foram expostas no passado"))
    findings.append(("INFO", "Nenhuma credencial ou volume foi alterado"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditar segredos sem exibir valores")
    parser.add_argument("--permitir-llm", action="store_true",
                        help="Nao alertar se OPENAI_API_KEY estiver preenchida")
    args = parser.parse_args()
    results = audit(ROOT, require_no_llm=not args.permitir_llm)
    print("AUDITORIA LOCAL (SOMENTE LEITURA)")
    for level, description in results:
        print(level + ": " + description)
    if any(level == "FAIL" for level, _ in results):
        print("RESULTADO: REQUER CORRECAO")
        return 1
    print("RESULTADO: SEM FALHAS ESTRUTURAIS DETECTADAS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
