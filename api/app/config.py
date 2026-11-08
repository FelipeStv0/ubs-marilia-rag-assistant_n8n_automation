import json
import os
from pathlib import Path
from urllib.parse import urlsplit

ALLOWED_HOSTS = {
    "www.marilia.sp.gov.br",
    "saude.marilia.sp.gov.br",
    "www.gov.br",
}


def sources():
    path = Path(os.getenv("SOURCES_CONFIG", "/app/sources.json"))
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("sources.json deve conter uma lista nao vazia")
    for item in raw:
        url = urlsplit(item["url"])
        if url.scheme != "https" or url.hostname not in ALLOWED_HOSTS or url.username or url.password:
            raise ValueError(f"Fonte nao autorizada: {item['url']}")
        if len(item["id"]) > 80 or not item["id"].replace("_", "").isalnum():
            raise ValueError("ID de fonte invalido")
    if len({s["id"] for s in raw}) != len(raw):
        raise ValueError("IDs de fonte duplicados")
    return raw


def openai_key():
    return os.getenv("OPENAI_API_KEY", "").strip()
