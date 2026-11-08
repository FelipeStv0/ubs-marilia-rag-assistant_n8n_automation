# Histórico de alterações

## Versão de revisão técnica — 2026-11-08

### Atualizado
- Documentação integral de arquitetura, instalação, operação, limites e segurança.
- Comunicação explícita do estado de testes: **sem chave de API externa paga**, com busca lexical e trechos oficiais.
- Correspondência por nome de UBS/USF mais restrita, para reduzir referências a unidades incorretas.
- Validação formal de IDs, URLs, categorias, prioridades e datas das fontes autorizadas.
- Verificação de redirects e controle de tamanho do HTML durante a transferência.
- Interface informa o modo de operação retornado pelo backend.

### Adicionado
- Testes de validação de fontes e modo extrativo.
- Integração contínua no GitHub Actions.
- Regras de quebra de linhas e contexto de build Docker.
- Guias em `docs/ARQUITETURA.md` e `docs/OPERACAO.md`.

### Pendente
- Testes de integração em Docker com banco e n8n.
- Gestão estruturada de conflitos de fontes e datas de vigência.
- Procedimento de backup e restauração validado em ambiente separado.

## Versão inicial

- Ambiente Docker Compose com n8n, FastAPI, PostgreSQL/pgvector e Nginx.
- Workflows para coleta agendada e atendimento.
- Busca textual sem LLM e caminho opcional para embeddings e geração.
