import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'api'))
from app.collector import extract_text, split_chunks
from app.rag import keywords, unit_name


def test_units_split_and_ignore_pharmacies():
    html = '<html><body><main>' + ''.join(
        f'<p>UBS UNIDADE {x}</p><p>Rua Teste {x}</p><p>Horário de Atendimento: 07h às 17h</p>'
        for x in range(6)) + '<h2>FARMÁCIAS MUNICIPAIS</h2><p>Farmácia Teste</p></main></body></html>'
    text = extract_text(html, 'unidades')
    parts = split_chunks(text, 'unidades')
    assert len(parts) == 6
    assert all('Farmácia Teste' not in part for part in parts)
    assert 'Rua Teste 0' in parts[0]


def test_units_query():
    assert unit_name('Qual o horário da UBS Castelo Branco?') == 'castelo branco'
    assert 'cpf' in keywords('Quais documentos devo levar?')


def test_regular_chunking():
    chunks = split_chunks('Vacinação e documentos oficiais. ' * 120, 'vacinacao', size=230, overlap=40)
    assert len(chunks) > 4
    assert all(len(c) < 300 for c in chunks)
