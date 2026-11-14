"""Coleta somente URLs aprovadas; não segue links arbitrários nem apaga dados em falhas."""
from __future__ import annotations
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from .config import ALLOWED_HOSTS, sources
from .db import connect
from .llm import embed_many

LOGGER = logging.getLogger(__name__)
USER_AGENT = "UBS-Marilia-Assistente-Academico/1.0 (coleta periodica; somente fontes oficiais)"
# Interface pública preservada: scripts e testes ainda importam do collector.
from .text_processing import UNIT_START, OTHER_SECTION, extract_text, split_chunks



def _safe_get(url: str) -> str:
    """Acessa apenas domínios aprovados; restringe redirecionamentos e tamanho."""
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
    })
    current = url
    max_bytes = 4_000_000
    try:
        for _ in range(4):
            parsed = urlsplit(current)
            if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
                    or parsed.username or parsed.password or parsed.port not in (None, 443)):
                raise ValueError("Redirecionamento para endereco nao permitido")
            with sess.get(current, timeout=(8, 30), allow_redirects=False, stream=True) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    redirect = response.headers.get("Location")
                    if not redirect:
                        raise ValueError("Redirecionamento sem URL")
                    current = urljoin(current, redirect)
                    continue
                response.raise_for_status()
                if "html" not in response.headers.get("Content-Type", "").lower():
                    raise ValueError("Conteudo retornado nao e HTML")
                length = response.headers.get("Content-Length")
                if length and length.isdigit() and int(length) > max_bytes:
                    raise ValueError("Pagina excedeu limite de 4 MB")
                pieces = []
                total = 0
                for part in response.iter_content(chunk_size=65536):
                    if not part:
                        continue
                    total += len(part)
                    if total > max_bytes:
                        raise ValueError("Pagina excedeu limite de 4 MB")
                    pieces.append(part)
                raw = b"".join(pieces)
                if not raw:
                    raise ValueError("Pagina vazia")
                encoding = response.encoding or response.apparent_encoding or "utf-8"
                return raw.decode(encoding, errors="replace")
        raise ValueError("Excesso de redirecionamentos")
    finally:
        sess.close()


def ingest_all():
    config = sources()
    summary = {"total": len(config), "updated": 0, "unchanged": 0, "failed": 0, "sources": []}
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(47392011) AS acquired")
            if not cur.fetchone()["acquired"]:
                return {"status": "already_running", **summary}
        conn.commit()
        try:
            for item in config:
                result = ingest_one(conn, item)
                summary["sources"].append(result)
                summary[result["status"]] = summary.get(result["status"], 0) + 1
        finally:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(47392011)")
            conn.commit()
    return summary


def ingest_one(conn, source):
    sid = source["id"]
    started = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO ubs.sources (source_id,url,title,category,priority,published_at)
          VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (source_id) DO UPDATE SET
          url=EXCLUDED.url,title=EXCLUDED.title,category=EXCLUDED.category,
          priority=EXCLUDED.priority,published_at=EXCLUDED.published_at""",
            (sid, source["url"], source["title"], source["category"], source.get("priority", 50), source.get("published_at")))
    conn.commit()
    try:
        html = _safe_get(source["url"])
        text = extract_text(html, source["category"])
        chunks = split_chunks(text, source["category"])
        if len(text) < 150 or not chunks:
            raise ValueError("Extracao muito curta; dados anteriores preservados")
        if source["category"] == "unidades" and len(chunks) < 5:
            raise ValueError("Poucas unidades extraidas; pagina pode ter mudado")
        digest = hashlib.sha256("\n\n".join(chunks).encode("utf-8")).hexdigest()
        with conn.cursor() as cur:
            cur.execute("SELECT content_hash FROM ubs.sources WHERE source_id=%s", (sid,))
            row = cur.fetchone()
            if row and row["content_hash"] == digest:
                # Se a chave de IA foi adicionada depois, gere vetores sem baixar tudo novamente.
                from .config import openai_key
                if openai_key():
                    cur.execute("""SELECT id,body FROM ubs.passages
                        WHERE source_id=%s AND active AND embedding IS NULL ORDER BY chunk_index""", (sid,))
                    pending = cur.fetchall()
                    if pending:
                        try:
                            missing = embed_many([r["body"] for r in pending])
                            if missing:
                                for passage, vec in zip(pending, missing):
                                    cur.execute("UPDATE ubs.passages SET embedding=%s::vector WHERE id=%s",
                                                (json.dumps(vec), passage["id"]))
                        except Exception as exc:
                            LOGGER.warning("Nao foi possivel completar embeddings de %s: %s", sid, type(exc).__name__)
                cur.execute("""UPDATE ubs.sources SET last_checked_at=now(),last_success_at=now(),
                    last_error=NULL,status='ok' WHERE source_id=%s""", (sid,))
                cur.execute("""INSERT INTO ubs.ingestion_runs(source_id,finished_at,outcome,details)
                    VALUES (%s,now(),'unchanged',%s)""", (sid, f"{len(chunks)} trechos; hash inalterado"))
                conn.commit()
                return {"source": sid, "status": "unchanged", "chunks": len(chunks)}
        try:
            vectors = embed_many(chunks)
        except Exception as exc:
            LOGGER.warning("Sem embeddings para %s, operando busca lexical: %s", sid, type(exc).__name__)
            vectors = None
        with conn.transaction():
            with conn.cursor() as cur:
                # Nenhuma revisao anterior e removida: fica inativa para auditoria.
                cur.execute("UPDATE ubs.passages SET active=FALSE WHERE source_id=%s", (sid,))
                for idx, content in enumerate(chunks):
                    vector = json.dumps(vectors[idx]) if vectors else None
                    cur.execute("""INSERT INTO ubs.passages
                        (source_id,revision_hash,chunk_index,body,embedding,active)
                        VALUES (%s,%s,%s,%s,%s::vector,TRUE)
                        ON CONFLICT(source_id,revision_hash,chunk_index)
                        DO UPDATE SET body=EXCLUDED.body, embedding=COALESCE(EXCLUDED.embedding, ubs.passages.embedding),
                        active=TRUE""", (sid, digest, idx, content, vector))
                cur.execute("""UPDATE ubs.sources SET content_hash=%s,chunk_count=%s,status='ok',
                    last_checked_at=now(),last_success_at=now(),last_changed_at=now(),last_error=NULL
                    WHERE source_id=%s""", (digest, len(chunks), sid))
                cur.execute("""INSERT INTO ubs.ingestion_runs(source_id,finished_at,outcome,details)
                    VALUES (%s,now(),'updated',%s)""", (sid, f"{len(chunks)} trechos"))
        return {"source": sid, "status": "updated", "chunks": len(chunks)}
    except Exception as exc:
        LOGGER.exception("Falha coletando %s", sid)
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute("""UPDATE ubs.sources SET last_checked_at=now(), status='error',
                last_error=%s WHERE source_id=%s""", (str(exc)[:500], sid))
            cur.execute("""INSERT INTO ubs.ingestion_runs(source_id,finished_at,outcome,details)
                VALUES (%s,now(),'failed',%s)""", (sid, str(exc)[:500]))
        conn.commit()
        return {"source": sid, "status": "failed", "error": str(exc)[:200]}
