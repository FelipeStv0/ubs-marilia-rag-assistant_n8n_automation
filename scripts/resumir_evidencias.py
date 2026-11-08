"""Gera resumo sanitizado de teste LOCAL sem incluir respostas, trechos ou segredos."""
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

HOSTS = {"www.marilia.sp.gov.br", "saude.marilia.sp.gov.br", "www.gov.br"}
CASES = {"endereco_ubs", "documentos_vacina", "unidade_inexistente", "emergencia"}


def summarize(report):
    if not isinstance(report, dict) or not isinstance(report.get("cases"), list):
        raise ValueError("Relatorio nao contem lista de casos")
    cases = report["cases"]
    if len(cases) != 4 or {x.get("case") for x in cases if isinstance(x, dict)} != CASES:
        raise ValueError("Conjunto de casos incorreto ou repetido")
    if report.get("mode") != "extractive_lexical":
        raise ValueError("Modo de operacao nao e o modo extrativo")
    if report.get("result") not in ("PASSOU", "FALHOU"):
        raise ValueError("Resultado geral invalido")
    lines = [
        "# Resumo sanitizado da validacao local", "",
        "Relatorio derivado de arquivo produzido no computador do operador. ",
        "O resumo omite respostas, perguntas completas, trechos e dados pessoais.", "",
        "Modo: extrativo/lexical; LLM desativada.",
        "Resultado geral declarado: " + report["result"], "",
        "Caminho de atendimento: Nginx > webhook n8n 02 > FastAPI > PostgreSQL.",
        "Workflow n8n 01: coleta avaliada separadamente no painel do n8n.", "",
        "| Cenario | HTTP | Modo | Resultado | Fontes devolvidas |",
        "|---|---:|---|---|---:|",
    ]
    failed = False
    for item in cases:
        if item.get("result") not in ("PASSOU", "FALHOU"):
            raise ValueError("Resultado de cenario invalido")
        sources = item.get("sources")
        if not isinstance(sources, list):
            raise ValueError("Lista de fontes ausente")
        for source in sources:
            if not isinstance(source, dict):
                raise ValueError("Fonte invalida")
            url = urlsplit(str(source.get("url") or ""))
            if url.scheme != "https" or url.hostname not in HOSTS:
                raise ValueError("URL de fonte fora da allowlist")
        mode = item.get("mode")
        if mode not in ("extractive", "no_evidence", "safety"):
            raise ValueError("Modo inesperado")
        failed = failed or item["result"] == "FALHOU"
        http = item.get("http_status")
        http = str(http) if isinstance(http, int) else "indisponivel"
        lines.append("| " + item["case"] + " | " + http + " | " + mode + " | " + item["result"] + " | " + str(len(sources)) + " |")
    for key, label in (("status", "Status da base"), ("blocked_method", "GET bloqueado")):
        check = report.get(key)
        if not isinstance(check, dict) or check.get("result") not in ("PASSOU", "FALHOU"):
            raise ValueError("Verificacao ausente: " + label)
        failed = failed or check["result"] == "FALHOU"
        http = check.get("http_status")
        lines.append("| " + label + " | " + (str(http) if isinstance(http, int) else "indisponivel") + " | - | " + check["result"] + " | - |")
    if failed and report["result"] == "PASSOU":
        raise ValueError("Inconsistencia entre casos e resultado geral")
    lines.extend(["", "## Limites", "",
        "Os resultados nao comprovam atualidade ou veracidade factual dos textos de origem.",
        "Nenhum trecho integral foi publicado; auditoria semantica depende dos artefatos privados.",
        "Nao representa homologacao de ambiente de producao, avaliacao clinica nem uso de LLM.",
        ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Resumo local seguro dos testes")
    parser.add_argument("--entrada", default="artifacts/execucao-real.json")
    parser.add_argument("--saida", default="artifacts/resumo-publicavel.md")
    args = parser.parse_args()
    inp, out = Path(args.entrada), Path(args.saida)
    if inp.resolve() == out.resolve():
        parser.error("Entrada e saida nao podem ser iguais")
    try:
        summary = summarize(json.loads(inp.read_text(encoding="utf-8")))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(summary, encoding="utf-8")
    except (OSError, ValueError) as exc:
        print("Falha ao gerar resumo: " + str(exc), file=sys.stderr)
        return 1
    print("Resumo criado em " + str(out) + ". Revise antes de publicar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
