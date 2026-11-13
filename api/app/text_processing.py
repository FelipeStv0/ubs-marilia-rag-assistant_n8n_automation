"""Extração de HTML e divisão em passagens para indexação.

INTEGRAÇÃO FUTURA: novos formatos de fonte devem ser normalizados aqui, antes
de chegar à camada de persistência. Preserve a separação de unidades de saúde
para não atribuir dados de outra instituição à unidade solicitada.
"""
from __future__ import annotations

import re
from bs4 import BeautifulSoup

UNIT_START = re.compile(r"^(?:UBS|USF)\s+[A-ZÀ-Ü0-9]", re.I)
OTHER_SECTION = re.compile(r"^(?:FARM[ÁA]CIAS MUNICIPAIS|OUTROS SERVI[ÇC]OS FARMAC[ÊE]UTICOS|FARM[ÁA]CIAS DISTRITAIS)", re.I)

def _clean_lines(lines):
    items = []
    for line in lines:
        line = re.sub(r"[ \t\xa0]+", " ", line).strip(" \t\r•")
        if line and (not items or line != items[-1]):
            items.append(line)
    return items


def extract_text(html: str, category: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "form", "iframe"]):
        tag.decompose()
    candidates = []
    for selector in ("article", "main", "[role='main']", ".conteudo", ".content", "#content"):
        for el in soup.select(selector):
            value = el.get_text("\n", strip=True)
            if len(value) > 200:
                candidates.append((len(value), value))
    # Um bloco de artigo curto pode ser mais limpo que todo o <body>.
    if candidates:
        article = [x for x in candidates if 200 < x[0] < 450000]
        raw = max(article, key=lambda x: x[0])[1] if article else (soup.body or soup).get_text("\n", strip=True)
    else:
        raw = (soup.body or soup).get_text("\n", strip=True)
    lines = _clean_lines(raw.splitlines())
    if category == "unidades":
        start = next((i for i, line in enumerate(lines) if UNIT_START.match(line)), None)
        if start is not None:
            lines = lines[start:]
        # Não misturar horários de farmácias com horários de unidades.
        stop = next((i for i, line in enumerate(lines) if OTHER_SECTION.match(line)), None)
        if stop is not None:
            lines = lines[:stop]
    return "\n".join(lines)


def split_chunks(text: str, category: str, size=1200, overlap=150) -> list[str]:
    if category == "unidades":
        lines = text.splitlines()
        groups = []
        current = []
        for line in lines:
            if UNIT_START.match(line) and current:
                groups.append("\n".join(current))
                current = []
            current.append(line)
        if current:
            groups.append("\n".join(current))
        groups = [g for g in groups if UNIT_START.match(g) and len(g) >= 45]
        if len(groups) >= 5:
            return [g[:2200] for g in groups][:250]
    # Janelas de caracteres que mantêm o contexto e evitam cortar tantas frases.
    text = text[:130000]
    output = []
    pos = 0
    while pos < len(text):
        end = min(pos + size, len(text))
        if end < len(text):
            cut = max(text.rfind("\n", pos + size // 2, end), text.rfind(". ", pos + size // 2, end))
            if cut > pos + size // 2:
                end = cut + 1
        block = text[pos:end].strip()
        if len(block) >= 65:
            output.append(block)
        if end >= len(text) or len(output) >= 140:
            break
        pos = max(pos + 1, end - overlap)
    return output
