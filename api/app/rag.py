"""Recuperacao hibrida: FTS/trigrama + cosseno opcional; geracao condicionada a fontes."""
from __future__ import annotations
import json
import logging
import math
import re
import unicodedata
from datetime import datetime, timezone
from .config import openai_key
from .db import connect
from .llm import embed_many, complete_with_evidence

LOGGER = logging.getLogger(__name__)
NO_EVIDENCE = (
    "Não encontrei evidências oficiais suficientes nas fontes cadastradas para confirmar essa informação. "
    "Consulte a Secretaria Municipal da Saúde ou a unidade responsável."
)
STOP = {
    "qual", "quais", "quando", "onde", "como", "quanto", "pode", "posso", "sobre", "para", "uma", "um", "com", "que", "das", "dos", "aos",
    "uma", "essa", "esse", "marilia", "marília", "cidade", "unidade", "unidades", "saude", "saúde", "posto", "postos", "tem", "sao", "são",
    "fica", "fazer", "preciso", "necessario", "necessários", "quero", "vou", "meu", "minha", "esta", "está", "mais", "por", "da", "de", "do", "em", "na", "no", "e", "o", "a", "se", "ao"
}
ALIASES = {
    "endereco": ["rua", "avenida", "av", "localizacao"],
    "endereço": ["rua", "avenida", "localização"],
    "documentos": ["carteira", "cartao", "cpf", "sus"],
    "documento": ["carteira", "cartao", "cpf", "sus"],
    "vacinar": ["vacinacao", "vacina"],
    "vacinação": ["vacina", "vacinacao"],
    "horário": ["atendimento", "funcionamento", "horario"],
    "horario": ["atendimento", "funcionamento"],
}
EMERGENCY = re.compile(r"(?:dor no peito|desmai|convuls|falta de ar|nao respiro|não respiro|suicid|sangramento intenso)", re.I)


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def keywords(query: str):
    terms = re.findall(r"[a-z0-9]{2,}", normalize(query))
    result = [t for t in terms if t not in STOP]
    for term in list(result):
        result.extend(normalize(v) for v in ALIASES.get(term, []))
    return list(dict.fromkeys(result))[:18]


def unit_name(query: str) -> str | None:
    q = normalize(query)
    match = re.search(r"\b(?:ubs|usf)\s+(?:do |da |de )?([a-z0-9 ]+)", q)
    if not match:
        return None
    text = match.group(1).strip()
    text = re.split(r"\b(?:fica|abre|tem|funciona|atende|horario|endereco|telefone|vacina|fecha)\b", text)[0].strip()
    return text or None


def _retrieve(question: str, vector: list[float] | None):
    terms = keywords(question)
    if not terms:
        return []
    query_or = " | ".join(terms[:10])
    qplain = " ".join(terms)
    result = {}
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT p.id,p.body,s.title,s.url,s.category,s.published_at,
                   s.last_success_at,s.priority,
                   ts_rank(to_tsvector('portuguese', p.body), to_tsquery('portuguese', %s)) AS ft,
                   word_similarity(lower(%s),lower(p.body)) AS word_sim
                FROM ubs.passages p JOIN ubs.sources s ON s.source_id=p.source_id
                WHERE p.active AND (to_tsvector('portuguese',p.body) @@ to_tsquery('portuguese', %s)
                    OR word_similarity(lower(%s),lower(p.body)) >= 0.08)
                ORDER BY (ts_rank(to_tsvector('portuguese',p.body),to_tsquery('portuguese', %s)) * 2
                    + word_similarity(lower(%s),lower(p.body))) DESC
                LIMIT 35""", (query_or, qplain, query_or, qplain, query_or, qplain))
            for row in cur.fetchall():
                result[row["id"]] = dict(row)
            if vector is not None:
                encoded = json.dumps(vector)
                cur.execute("""SELECT p.id,p.body,s.title,s.url,s.category,s.published_at,
                    s.last_success_at,s.priority,
                    1 - (p.embedding <=> %s::vector) AS vec_sim
                    FROM ubs.passages p JOIN ubs.sources s ON s.source_id=p.source_id
                    WHERE p.active AND p.embedding IS NOT NULL
                    ORDER BY p.embedding <=> %s::vector LIMIT 24""", (encoded, encoded))
                for row in cur.fetchall():
                    if row["id"] in result:
                        result[row["id"]]["vec_sim"] = float(row["vec_sim"])
                    else:
                        result[row["id"]] = dict(row)
    unit = unit_name(question)
    ranked = []
    for row in result.values():
        content = normalize(row["body"])
        hits = sum(1 for t in terms if t in content)
        primary = [t for t in terms if t not in {"ubs", "usf", "horario", "atendimento", "vacina", "vacinacao", "cartao", "cpf", "sus"}]
        primary_hits = sum(1 for t in primary if t in content)
        score = float(row.get("ft") or 0) * 2 + float(row.get("word_sim") or 0)
        score += hits * 0.11 + primary_hits * 0.13
        score += max(0, float(row.get("vec_sim") or 0) - 0.40) * 1.15
        score += (row["priority"] or 0) / 1000
        # Evita responder a pergunta sobre uma UBS com dados de outra UBS.
        if unit:
            unit_tokens = [t for t in unit.split() if len(t) > 2 and t not in STOP]
            if unit_tokens and not all(t in content for t in unit_tokens):
                score *= 0.08
            elif unit_tokens:
                score += 0.8
        if score >= 0.36 and (hits or float(row.get("vec_sim") or 0) > 0.54):
            row["score"] = round(score, 4)
            ranked.append(row)
    ranked.sort(key=lambda item: item["score"], reverse=True)
    if unit:
        # Se só existem coincidências fracas, não citar outra unidade.
        ranked = [r for r in ranked if r["score"] >= 0.60]
    return ranked[:8]


def _public_source(row):
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "url": row["url"],
        "excerpt": row["body"][:650],
        "published_at": str(row["published_at"]) if row["published_at"] else None,
        "checked_at": row["last_success_at"].isoformat() if row["last_success_at"] else None,
    }


def answer(question: str) -> dict:
    question = question.strip()
    if EMERGENCY.search(question):
        return {
            "answer": "Este assistente fornece apenas informações administrativas e não avalia sintomas. "
                      "Se houver risco imediato à vida, acione o SAMU pelo telefone 192.",
            "sources": [{"id": "orientacao-urgencia", "title": "Prefeitura de Marília — serviços de urgência", "url":
                         "https://www.marilia.sp.gov.br/portal/noticias/0/3/17363/secretaria-da-saude-promove-encontro-para-divulgar-acoes-de-valorizacao-da-vida-no-municipio/",
                         "excerpt": "SAMU — serviço de atendimento móvel de urgência; telefone 192.",
                         "published_at": None, "checked_at": None}],
            "mode": "safety", "sufficient": True,
        }
    vector = None
    if openai_key():
        try:
            vector = embed_many([question])[0]
        except Exception as exc:
            LOGGER.warning("Embeddings indisponiveis, fallback lexical: %s", type(exc).__name__)
    evidence = _retrieve(question, vector)
    if not evidence:
        return {"answer": NO_EVIDENCE, "sources": [], "mode": "no_evidence", "sufficient": False}
    if not openai_key():
        best = evidence[0]
        return {
            "answer": "Encontrei este trecho de uma fonte oficial (modo sem LLM):\n\n" + best["body"][:850],
            "sources": [_public_source(best)], "mode": "extractive", "sufficient": True,
        }
    try:
        payload = complete_with_evidence(question, evidence)
        allowed = {str(p["id"]): p for p in evidence}
        ids = [str(x) for x in payload.get("used_source_ids", [])]
        verified = [allowed[x] for x in dict.fromkeys(ids) if x in allowed]
        if not payload.get("sufficient") or not verified:
            return {"answer": NO_EVIDENCE, "sources": [], "mode": "no_evidence", "sufficient": False}
        message = str(payload.get("answer") or "").strip()[:2600]
        if len(message) < 5:
            raise ValueError("Resposta vazia")
        return {"answer": message, "sources": [_public_source(x) for x in verified[:5]],
                "mode": "rag", "sufficient": True}
    except Exception:
        LOGGER.exception("Falha ao gerar resposta")
        return {
            "answer": "A consulta encontrou documentos, mas a etapa de geração não está disponível no momento. "
                      "Confira os trechos oficiais apresentados abaixo.",
            "sources": [_public_source(x) for x in evidence[:3]],
            "mode": "generation_error", "sufficient": False,
        }
