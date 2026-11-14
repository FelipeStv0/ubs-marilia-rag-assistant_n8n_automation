# Guia de manutenção e integração — Assistente UBS

## Mapa de responsabilidades

| Módulo | Responsabilidade | Ponto seguro de extensão |
| --- | --- | --- |
| `api/app/main.py` | Rotas HTTP e contratos de entrada/saída | Novos endpoints e schemas Pydantic |
| `api/app/config.py` | Fontes autorizadas, categorias e credenciais | Alterar lista permitida com revisão de segurança |
| `api/app/collector.py` | Orquestrar coleta, hashes, revisões e transações | Novas políticas de ingestão; preservar rollback |
| `api/app/text_processing.py` | Extrair HTML e separar passagens | Adicionar novos seletores, tipos de seção e testes |
| `api/app/query_policy.py` | Normalizar pergunta e validar evidência mínima | Ampliar sinônimos e intenções com exemplos negativos |
| `api/app/rag.py` | Buscar, ordenar e responder a partir de evidências | Mudanças de ranking e limiares, sempre com testes de relevância |
| `api/app/llm.py` | Chamadas opcionais a embeddings e geração | Troca de provedores mediante contrato validado |
| `api/app/db.py` | Abrir conexão com PostgreSQL | Configurações de conexão e pool, com testes |

## Contratos a preservar

- Endpoints `/health`, `/internal/status`, `/internal/reindex` e `/internal/answer` são usados pelo n8n; não renomear sem migrar os workflows.
- `collector.extract_text`, `collector.split_chunks`, `rag.keywords` e `rag.location_supported` continuam importáveis por compatibilidade; os módulos específicos são suas novas fontes de implementação.
- Sem chave de API, o comportamento padrão continua **extrativo/lexical**: não declarar geração por LLM como ativa.
- Revisões antigas permanecem disponíveis para auditoria; falhas de coleta não apagam documentos anteriores.
- Fonte citada não implica verdade clínica ou atualização garantida; perguntas sem evidência devem permitir abstenção.

## Alterar com segurança

1. Crie um branch e modifique o módulo dono da regra, sem duplicar lógica nos workflows.
2. Acrescente testes para resultado esperado **e** falso positivo (por exemplo, endereço solicitado e somente horário disponível).
3. Execute `python -m pytest -q tests` com as dependências de desenvolvimento instaladas; confira `.github/workflows/ci.yml`.
4. Para alterações de n8n, mantenha credenciais privadas e valide a integração em ambiente isolado antes de migrar contêineres.
5. Registre no PR o cenário testado, a limitação do teste e como reverter a mudança.

Este é um protótipo independente para informações administrativas, sem diagnóstico médico e sem vínculo institucional oficial.
