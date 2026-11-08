"""Smoke test real: Nginx -> webhook n8n -> FastAPI -> PostgreSQL.

Registra as respostas efetivamente recebidas, sem inventar saídas. Não usa LLM.
Exige Docker Compose local, workflow 02 publicado e fontes previamente indexadas.
"""
import argparse
import json
import re
import unicodedata
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ALLOWED = {"www.marilia.sp.gov.br", "saude.marilia.sp.gov.br", "www.gov.br"}
CASES = [
    ("endereco_ubs", "Onde fica a UBS Castelo Branco?", "extractive", True),
    ("documentos_vacina", "Quais documentos devo levar para vacinação?", "extractive", True),
    ("unidade_inexistente", "Qual o endereço da UBS Inexistente Arco Iris 999?", "no_evidence", False),
    ("emergencia", "Estou com dor no peito", "safety", False),
]


def call(base, path, method="GET", payload=None):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
    headers = {"Content-Type": "application/json"} if data else {}
    started = time.monotonic()
    req = Request(base.rstrip("/") + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=110) as response:
            status, raw = response.status, response.read(200000)
    except HTTPError as exc:
        status, raw = exc.code, exc.read(200000)
    except (URLError, OSError, TimeoutError) as exc:
        return {"http_status": None, "latency_ms": round((time.monotonic()-started)*1000),
                "error": f"{type(exc).__name__}: {str(exc)[:250]}"}
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        decoded = None
    return {"http_status": status, "latency_ms": round((time.monotonic()-started)*1000),
            "data": decoded}


def official_source(source):
    if not isinstance(source, dict):
        return False
    try:
        url = urlsplit(source["url"])
        return (url.scheme == "https" and url.hostname in ALLOWED
                and bool(source.get("title")) and bool(source.get("excerpt"))
                and bool(source.get("checked_at")))
    except (KeyError, ValueError, TypeError):
        return False


def normalize(text):
    return "".join(char for char in unicodedata.normalize("NFKD", text.lower())
                   if not unicodedata.combining(char))


def semantic_check(name, answer):
    """Minimal deterministic evidence checks, not independent factual verification."""
    text = normalize(answer or "")
    if name == "endereco_ubs":
        # Mentioning a unit or its opening hours alone is NOT an address.
        if re.search(r"\b(?:rua|avenida|av\.?|travessa|alameda|praca|rodovia|estrada)\b", text):
            return True, "Resposta contém indicação de logradouro (verificação heurística)."
        return False, "Pergunta de endereço sem logradouro no trecho recuperado."
    if name == "documentos_vacina":
        if "carteira de vacinacao" in text and ("cpf" in text or "cartao sus" in text):
            return True, "Resposta menciona documentos de vacinação."
        return False, "Trecho não informa documentos suficientes."
    return True, "Cenário de segurança/abstenção verificado estruturalmente."


def evaluate(base, case):
    name, question, expected, needs_source = case
    resp = call(base, "/api/chat", "POST", {"question": question})
    body = resp.get("data")
    body = body if isinstance(body, dict) else {}
    sources = body.get("sources")
    sources = sources if isinstance(sources, list) else []
    success = (resp["http_status"] == 200 and body.get("mode") == expected
               and isinstance(body.get("answer"), str) and bool(body["answer"].strip())
               and body.get("sufficient") is (expected in ("extractive", "safety")))
    if needs_source:
        success = (success and bool(sources) and all(official_source(s) for s in sources)
                   and "sem API de IA" in body.get("answer", ""))
    else:
        success = success and sources == []
    semantic_ok, semantic_reason = semantic_check(name, body.get("answer"))
    success = success and semantic_ok
    return {
        "case": name, "question": question, "expected_mode": expected,
        "semantic_ok": semantic_ok, "semantic_reason": semantic_reason,
        "result": "PASSOU" if success else "FALHOU", "http_status": resp["http_status"],
        "latency_ms": resp["latency_ms"], "mode": body.get("mode"),
        "sufficient": body.get("sufficient"), "answer": body.get("answer"),
        "sources": sources, "error": resp.get("error")
    }


def reindex_backend():
    """Usa API dentro do Docker; não prova a execução do workflow n8n de coleta."""
    try:
        proc = subprocess.run(["docker", "compose", "exec", "-T", "api",
                               "python", "-m", "app.bootstrap"],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=300, check=False)
        output = json.loads(proc.stdout) if proc.returncode == 0 else None
        passed = (proc.returncode == 0 and isinstance(output, dict)
                  and output.get("failed") == 0 and output.get("total", 0) > 0)
        return {"result": "PASSOU" if passed else "FALHOU", "summary": output,
                "error": proc.stderr[-500:] if not passed else None}
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {"result": "FALHOU", "error": f"{type(exc).__name__}: {str(exc)[:250]}"}


def markdown(report):
    lines = [
        "# Evidência de execução real", "",
        "Gerado em (UTC): " + report["date_utc"], "",
        "Resultado geral: **" + report["result"] + "**", "",
        "Modo esperado: busca lexical extrativa, sem LLM.", "",
        "Caminho avaliado: Nginx → webhook n8n 02 → FastAPI → PostgreSQL.", "",
        "A automação de coleta do n8n 01 NÃO foi verificada por este script.", "",
        "## Resultado das verificações", "",
        "| Verificação | HTTP | Modo | Resultado |",
        "|---|---:|---|---|",
    ]
    status = report["status"]
    lines.append(f"| Base indexada | {status.get('http_status')} | {report['mode']} | {status['result']} |")
    for case in report["cases"]:
        lines.append(f"| {case['case']} | {case['http_status']} | {case.get('mode')} | {case['result']} |")
    blocked = report["blocked_method"]
    lines.append(f"| GET bloqueado no chat | {blocked['http_status']} | nginx | {blocked['result']} |")
    lines.extend(["", "## Avaliação mínima de relevância", "",
                  "A aprovação HTTP e o retorno de fonte não garantem resposta à intenção da pergunta.", ""])
    for case in report["cases"]:
        lines.append("- " + case["case"] + ": " + case.get("semantic_reason", "não avaliada"))
    lines.extend(["", "## Perguntas, respostas e fontes efetivamente retornadas", ""])
    for case in report["cases"]:
        lines.append("### " + case["case"] + " — " + case["result"])
        lines.append("")
        lines.append("**Pergunta:** " + case["question"])
        lines.append("")
        lines.append("**Resposta:**")
        lines.append("")
        lines.append("> " + (case.get("answer") or "[sem resposta]").replace("\n", "\n> ")[:2600])
        lines.append("")
        for src in case["sources"]:
            lines.append("- " + str(src.get("title", "Fonte")) + ": " + str(src.get("url", ""))
                         + " | última coleta bem-sucedida: " + str(src.get("checked_at"))
                         + " | estado da fonte: " + str(src.get("source_status", "não informado")))
        if not case["sources"]:
            lines.append("- Sem fontes retornadas.")
        lines.append("")
    lines.extend([
        "## Limites", "",
        "Testes do HTTP local não comprovam atualidade de informações da Prefeitura, ",
        "execução do agendamento do workflow 01, integração com LLM ou operação pública. ",
        "As fontes podem mudar após a coleta. Caso uma coleta falhe, dados anteriores ",
        "podem permanecer na base e devem ser considerados potencialmente desatualizados.",
        ""
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Evidência real do modo extrativo")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--saida", default="artifacts/execucao-real.json")
    parser.add_argument("--coletar", action="store_true",
                        help="Executa coleta pelo backend Docker, não pelo n8n 01")
    args = parser.parse_args()
    collection = reindex_backend() if args.coletar else {"result": "NÃO EXECUTADA"}
    status = call(args.base_url, "/api/status")
    data = status.get("data") if isinstance(status.get("data"), dict) else {}
    valid_status = (status["http_status"] == 200
                    and data.get("rag_mode") == "extractive_lexical"
                    and isinstance(data.get("sources_ok"), int) and data["sources_ok"] > 0
                    and isinstance(data.get("passages"), int) and data["passages"] > 0)
    status["result"] = "PASSOU" if valid_status else "FALHOU"
    cases = [evaluate(args.base_url, case) for case in CASES]
    blocked = call(args.base_url, "/api/chat", "GET")
    blocked["result"] = "PASSOU" if blocked["http_status"] == 403 else "FALHOU"
    checks = [status["result"], blocked["result"]] + [case["result"] for case in cases]
    if args.coletar:
        checks.append(collection["result"])
    report = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url, "mode": data.get("rag_mode"),
        "collection": collection, "n8n_refresh_workflow": "NAO_VERIFICADO",
        "status": status, "cases": cases, "blocked_method": blocked,
        "result": "PASSOU" if all(x == "PASSOU" for x in checks) else "FALHOU",
    }
    outfile = Path(args.saida)
    outfile.parent.mkdir(parents=True, exist_ok=True)
    outfile.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    outfile.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    for case in cases:
        print(case["result"], case["case"], "HTTP", case["http_status"], case["mode"])
    print("RESULTADO", report["result"], "Evidências:", outfile, outfile.with_suffix(".md"))
    return 0 if report["result"] == "PASSOU" else 1


if __name__ == "__main__":
    sys.exit(main())
