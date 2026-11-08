"""Configuração e validação das fontes oficiais autorizadas."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

ALLOWED_HOSTS = frozenset({
    "www.marilia.sp.gov.br",
    "saude.marilia.sp.gov.br",
    "www.gov.br",
})
CATEGORIES = frozenset({"unidades", "horarios", "vacinacao", "orientacoes", "documentos"})
SOURCE_ID = re.compile(r"^[a-zA-Z0-9_]{1,80}$")


def validate_source(item: dict) -> dict:
    if not isinstance(item, dict):
        raise ValueError("Cada fonte deve ser um objeto JSON")
    required = ("id", "title", "url", "category")
    if any(not isinstance(item.get(k), str) or not item[k].strip() for k in required):
        raise ValueError("Fonte com id, title, url ou category ausente")
    if not SOURCE_ID.fullmatch(item["id"]):
        raise ValueError("ID de fonte invalido")
    url = urlsplit(item["url"])
    if (url.scheme != "https" or url.hostname not in ALLOWED_HOSTS
            or url.username or url.password or url.port not in (None, 443)
            or not url.path.startswith("/")):
        raise ValueError(f"Fonte nao autorizada: {item['id']}")
    if item["category"] not in CATEGORIES:
        raise ValueError(f"Categoria invalida: {item['id']}")
    priority = item.get("priority", 50)
    if isinstance(priority, bool) or not isinstance(priority, int) or not 0 <= priority <= 100:
        raise ValueError(f"Prioridade fora do intervalo 0-100: {item['id']}")
    published_at = item.get("published_at")
    if published_at is not None:
        from datetime import date
        try:
            date.fromisoformat(published_at)
        except (TypeError, ValueError):
            raise ValueError(f"Data de publicacao invalida: {item['id']}") from None
    return item


def sources() -> list[dict]:
    path = Path(os.getenv("SOURCES_CONFIG", "/app/sources.json"))
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("sources.json deve conter uma lista nao vazia")
    for item in raw:
        validate_source(item)
    ids = [s["id"] for s in raw]
    urls = [s["url"] for s in raw]
    if len(ids) != len(set(ids)) or len(urls) != len(set(urls)):
        raise ValueError("IDs ou URLs de fontes duplicados")
    return raw


def openai_key() -> str:
    return os.getenv("OPENAI_API_KEY", "").strip()
