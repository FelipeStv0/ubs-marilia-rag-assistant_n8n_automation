# Operação, atualização e diagnóstico

## Pré-requisitos

- Docker Desktop com WSL 2 habilitado, para Windows.
- Python 3.11+ e Docker Compose.
- Acesso à internet para buscar os endereços oficiais selecionados em `sources.json`.
- **Não é necessária** uma chave de API externa paga para o modo de testes.

## Primeira execução

```powershell
python scripts/gerar_env.py
docker compose up -d --build
docker compose ps
```

Abra `http://localhost:5678`, crie o usuário proprietário, importe os workflows em `workflows/` e clique em **Publish** em cada um. Para a primeira coleta, execute manualmente o workflow 01. Interface: `http://localhost:8080`.

> O script `scripts/iniciar_windows.ps1` orienta as etapas de instalação e importação.

## Verificações

```powershell
docker compose ps
docker compose logs --tail=100 api
docker compose logs --tail=100 n8n
docker compose exec -T api python -m app.bootstrap
```

A consulta `http://localhost:8080/api/status` informa quantidade de trechos ativos e fontes com coleta concluída, quando os serviços estiverem disponíveis. Se todos os indicadores forem zero, a ingestão pode ainda não ter ocorrido ou ter falhado.

## Atualização segura

1. **Antes de substituir os arquivos**, preserve o `.env` em um local seguro (fora do GitHub). Nunca altere `N8N_ENCRYPTION_KEY` sem um plano de migração de credenciais.
2. Faça backup dos volumes `postgres_data` e `n8n_data`. Para backups consistentes, use `pg_dump` para o PostgreSQL e o procedimento de backup recomendado para o n8n.
3. Atualize o código-fonte. Não apague `.env`, volumes ou dados.
4. Execute `docker compose up -d --build`.
5. Valide `docker compose ps`, os logs, a coleta manual e uma consulta no chat.
6. Caso o arquivo JSON de um workflow tenha mudado, revise as diferenças e importe/publice conscientemente; a alteração do JSON em disco não garante atualização de um workflow já salvo no n8n.

**Nota sobre SQL:** `db/init.sql` é executado automaticamente **somente na inicialização de um volume PostgreSQL novo**. Alterações futuras no esquema devem usar migrações versionadas; não remova volumes para aplicar mudanças.

## Erros comuns

| Sintoma | Diagnóstico |
|---|---|
| `localhost:5678` indisponível | Verificar Docker Desktop, `docker compose ps` e logs do n8n |
| `localhost:8080` mostra erro de chat | Verificar publicação do workflow 02, webhook de produção e logs |
| Nenhuma fonte indexada | Executar workflow 01 manualmente, verificar URLs e logs da API |
| Fonte marcada como erro | Layout alterado, HTTP indisponível, conteúdo vazio ou fora da allowlist |
| Resultado pouco específico | Revisar origem, trecho e pergunta; no modo sem LLM a resposta é extrativa |
| Workflow editado não refletiu no chat | Publicar a nova versão do workflow no n8n |
| Docker não inicia no Windows | Conferir WSL 2, virtualização e Docker Desktop |

## Testes

```powershell
python -m pip install -r api/requirements-dev.txt
python -m pytest -q tests/
python -m compileall -q api/app scripts
docker compose config
```

A automação GitHub Actions cobre testes unitários e estrutura. A validação integrada do n8n, Nginx, banco e coleta exige executar o Compose localmente.

## Demonstrar a execução completa

Para registrar um relatório reproduzível de consultas reais (HTTP através de Nginx, webhook n8n 02, API e PostgreSQL), confira [Demonstração e evidências](DEMONSTRACAO.md) e execute a partir da raiz:

    python scripts/validar_execucao.py

Após publicar os workflows e executar a ingestão, os resultados aparecerão em artifacts/execucao-real.json e artifacts/execucao-real.md. Esses arquivos não são incluídos no Git, e qualquer cenário reprovado permanece identificado como FALHOU.

A execução manual do workflow n8n 01 deve ser confirmada separadamente nas execuções do próprio n8n. Testes de FastAPI + PostgreSQL no CI não comprovam o agendamento n8n ou a coleta de páginas públicas.

## Privacidade e limites

Não inserir nomes, documentos, cartões SUS, diagnósticos ou dados clínicos no chat. O protótipo não é destinado a atender cidadãos pela internet sem revisão de segurança e governança. O horário da última verificação não demonstra que uma unidade esteja aberta neste momento; dados críticos devem ser confirmados diretamente na fonte oficial.
