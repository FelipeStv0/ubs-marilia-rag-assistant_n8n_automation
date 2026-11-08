"""Rotas internas não publicadas diretamente na Internet; exposição apenas por proxy n8n."""
from __future__ import annotations
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .collector import ingest_all
from .db import connect
from .rag import answer
from .config import openai_key

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
app = FastAPI(title="Assistente UBS Marília — serviço interno", docs_url=None, redoc_url=None)


class Question(BaseModel):
    question: str = Field(min_length=4, max_length=600)


@app.get("/health")
def health():
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS ok")
            cur.fetchone()
    return {"ok": True}


@app.get("/internal/status")
def status():
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT COUNT(*) AS total,
                COUNT(*) FILTER(WHERE status='ok') AS ok,
                COUNT(*) FILTER(WHERE status='error') AS errors,
                MAX(last_success_at) AS last_success
                FROM ubs.sources""")
            s = cur.fetchone()
            cur.execute("SELECT COUNT(*) AS total FROM ubs.passages WHERE active")
            passages = cur.fetchone()["total"]
    return {
        "sources": s["total"], "sources_ok": s["ok"], "sources_error": s["errors"],
        "passages": passages, "last_success": s["last_success"].isoformat() if s["last_success"] else None,
        "rag_mode": "llm_and_vector" if openai_key() else "extractive_lexical",
    }


@app.post("/internal/reindex")
def reindex():
    return ingest_all()


@app.post("/internal/answer")
def ask(payload: Question):
    return answer(payload.question)
