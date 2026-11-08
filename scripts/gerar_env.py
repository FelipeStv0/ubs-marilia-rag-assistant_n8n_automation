"""Prepara .env com segredos locais; não sobrescreve credenciais existentes."""
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[1]
template = (ROOT / '.env.example').read_text(encoding='utf-8')
path = ROOT / '.env'
if path.exists():
    content = path.read_text(encoding='utf-8')
else:
    content = template
for name, placeholder in (
    ('POSTGRES_PASSWORD', 'SUBSTITUIR_POR_SEGREDO_ALEATORIO'),
    ('N8N_ENCRYPTION_KEY', 'SUBSTITUIR_POR_CHAVE_DE_32_OU_MAIS_CARACTERES'),
):
    content = content.replace(f'{name}={placeholder}', f'{name}={secrets.token_urlsafe(36)}')
path.write_text(content, encoding='utf-8')
print('.env pronto. Configure OPENAI_API_KEY no arquivo para respostas com LLM e embeddings.')
