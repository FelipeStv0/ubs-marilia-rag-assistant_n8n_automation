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
# API pública preservada para integrações e testes existentes.
from .query_policy import (STOP, ALIASES, EMERGENCY, ADDRESS_LINE,
                           normalize, keywords, unit_name, location_requested,
                           location_supported)


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
                   s.last_success_at,s.priority,s.status,s.last_checked_at,
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
                    s.last_success_at,s.priority,s.status,s.last_checked_at,
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
            if unit_tokens and not all(re.search(r"\b" + re.escape(t) + r"\b", content) for t in unit_tokens):
                # Nunca atribuir dados de outra unidade ao nome solicitado.
                continue
            if unit_tokens:
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
        "source_status": row.get("status"),
        "last_attempt_at": row["last_checked_at"].isoformat() if row.get("last_checked_at") else None,
    }


def answer(question: str) -> dict:
    question = question.strip()
    if EMERGENCY.search(question):
        return {
            "answer": "Este assistente fornece apenas informações administrativas e não avalia sintomas. "
                      "Se houver risco imediato à vida, acione o SAMU pelo telefone 192.",
            "sources": [],
            "mode": "safety", "sufficient": True,
        }
    vector = None
    if openai_key():
        try:
            vector = embed_many([question])[0]
        except Exception as exc:
            LOGGER.warning("Embeddings indisponiveis, fallback lexical: %s", type(exc).__name__)
    evidence = _retrieve(question, vector)
    if location_requested(question):
        evidence = [item for item in evidence if location_supported(question, item)]
    if not evidence:
        return {"answer": NO_EVIDENCE, "sources": [], "mode": "no_evidence", "sufficient": False}
    if not openai_key():
        # Neste modo nao ha geracao: apresentar texto original sem parafrasear fatos.
        best = evidence[0]
        excerpt = best["body"][:1100].strip()
        if not excerpt:
            return {"answer": NO_EVIDENCE, "sources": [], "mode": "no_evidence", "sufficient": False}
        return {
            "answer": (
                "Modo de testes — sem API de IA. Trecho localizado em uma fonte oficial "
                "(confira a unidade, a vigencia e a fonte antes de utilizar):\n\n"
                + excerpt
            ),
            "sources": [_public_source(best)],
            "mode": "extractive",
            "sufficient": True,
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
