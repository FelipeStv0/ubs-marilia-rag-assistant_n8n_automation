import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from app.config import validate_source, sources


def valid_source():
    return {
        "id": "marilia_unidades",
        "title": "Prefeitura de Marília",
        "url": "https://www.marilia.sp.gov.br/portal/secretarias-paginas/16/unidades/",
        "category": "unidades",
        "priority": 80,
    }


def test_valid_official_source():
    assert validate_source(valid_source())["priority"] == 80


@pytest.mark.parametrize("url", [
    "http://www.marilia.sp.gov.br/page",
    "https://evil.example/page",
    "https://www.marilia.sp.gov.br.evil.example/page",
    "https://user:pass@www.marilia.sp.gov.br/page",
    "https://www.marilia.sp.gov.br:8080/page",
])
def test_reject_unauthorized_urls(url):
    item = valid_source()
    item["url"] = url
    with pytest.raises(ValueError):
        validate_source(item)


def test_reject_invalid_metadata():
    for key, value in [
        ("priority", 101), ("priority", True), ("category", "diagnostico"),
        ("published_at", "2026-13-40"), ("id", "nome com espacos"),
    ]:
        item = valid_source()
        item[key] = value
        with pytest.raises(ValueError):
            validate_source(item)


def test_reject_duplicate_source_ids(tmp_path, monkeypatch):
    import json
    path = tmp_path / "sources.json"
    path.write_text(json.dumps([valid_source(), valid_source()]), encoding="utf-8")
    monkeypatch.setenv("SOURCES_CONFIG", str(path))
    with pytest.raises(ValueError, match="duplicados"):
        sources()
