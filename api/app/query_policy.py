"""Políticas testáveis da consulta: normalização, intenção e evidência mínima.

INTEGRAÇÃO FUTURA: mantenha funções puras neste módulo; não faça acesso a banco
nem chamadas a LLM aqui. Mudanças na seleção de evidências devem ter testes.
"""
from __future__ import annotations

import re
import unicodedata

# Regras de interpretação da pergunta; ampliar apenas com exemplos de regressão.
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

# Evidência de localização evita confundir endereço com horário de atendimento.
# A busca lexical pode encontrar a unidade sem o dado solicitado (ex.: horário
# em vez de endereço). Não declarar suficiência se faltar evidência de localização.
ADDRESS_LINE = re.compile(r"\b(?:rua|avenida|av\.?|travessa|alameda|praca|rodovia|estrada)\b", re.I)


def location_requested(question: str) -> bool:
    text = normalize(question)
    return bool(re.search(r"\b(?:endereco|localizacao|onde\s+fica|qual\s+(?:a\s+)?rua)\b", text))


def location_supported(question: str, passage: dict) -> bool:
    """Conservative check: a location question needs an address near the unit name."""
    text = normalize(passage.get("body", ""))
    unit = unit_name(question)
    if unit:
        unit_pattern = re.compile(r"\b" + r"\s+".join(re.escape(x) for x in unit.split()) + r"\b")
        for match in unit_pattern.finditer(text):
            window = text[max(0, match.start() - 80):match.end() + 280]
            if ADDRESS_LINE.search(window):
                return True
        return False
    return bool(ADDRESS_LINE.search(text))
