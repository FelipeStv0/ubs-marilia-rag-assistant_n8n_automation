"""Static workflow contract tests; do NOT claim to execute n8n."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / "workflows" / name).read_text(encoding="utf-8"))


def test_chat_routes_match():
    nodes = {node["type"]: node for node in load("02-perguntas-rag.json")["nodes"]}
    assert nodes["n8n-nodes-base.webhook"]["parameters"]["path"] == "ubs-marilia"
    assert nodes["n8n-nodes-base.webhook"]["parameters"]["responseMode"] == "responseNode"
    assert nodes["n8n-nodes-base.httpRequest"]["parameters"]["url"] == "http://api:8000/internal/answer"
    assert nodes["n8n-nodes-base.respondToWebhook"]["parameters"]["respondWith"] == "firstIncomingItem"
    assert "proxy_pass http://n8n:5678/webhook/ubs-marilia;" in (
        ROOT / "nginx" / "default.conf"
    ).read_text(encoding="utf-8")


def test_refresh_has_manual_and_scheduled_paths():
    nodes = {node["type"]: node for node in load("01-atualizacao-fontes.json")["nodes"]}
    assert "n8n-nodes-base.manualTrigger" in nodes
    assert "n8n-nodes-base.scheduleTrigger" in nodes
    assert nodes["n8n-nodes-base.httpRequest"]["parameters"]["url"] == "http://api:8000/internal/reindex"
