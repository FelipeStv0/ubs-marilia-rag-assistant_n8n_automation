# Operação, atualização e diagnóstico

## Pré-requisitos

- Docker Desktop com WSL 2 habilitado, para Windows.
- Python 3.11+ e Docker Compose.
- Acesso à internet para buscar os endereços oficiais selecionados em `sources.json`.
- **Não é necessária** uma chave de API externa paga para o modo de testes.

## Inicialização com n8n migrado (09/11/2026)

A instalação documentada usa **dois projetos Compose**: principal (`db`, `api`, `web`) e privado (`ubs-n8n-novo`). **O n8n antigo está parado e não é iniciado automaticamente pelo Compose principal.** O Nginx agora encaminha `/api/chat` para `ubs-n8n-novo:5678`.

O `.env` da raiz continua contendo a senha de PostgreSQL; o `.env` da pasta privada de migração contém a nova chave de criptografia. **Não substitua nem misture esses arquivos.** Siga o [roteiro completo de migração](MIGRACAO_N8N.md).

```powershell
$pasta = "$HOME\Documents\UBS-Backup\migracao-n8n"
docker compose up -d --build db api
docker compose -f "$pasta\compose.yaml" up -d
docker compose up -d web
docker compose ps
docker compose -f "$pasta\compose.yaml" ps
python scripts/validar_execucao.py
```

O Nginx depende de o n8n novo existir na rede. **Não execute simplesmente `docker compose up -d` na primeira inicialização** antes de iniciar o n8n migrado. O comando `scripts/iniciar_windows.ps1` aplica a ordem segura e não gera senhas em ambiente existente.

## Verificações e diagnóstico

```powershell
$pasta = "$HOME\Documents\UBS-Backup\migracao-n8n"
docker compose ps -a
docker compose -f "$pasta\compose.yaml" ps
docker compose logs --tail=100 api
docker compose -f "$pasta\compose.yaml" logs --tail=100 n8n
docker compose exec -T web nginx -t
docker compose exec -T api ls -l /app/sources.json
```

O status do chat é `http://localhost:8080/api/status`, e o editor novo é `http://localhost:5679`.

## Atualização segura

1. Faça backup do `.env` antigo, do `.env` **novo**, do `automacao.backup`, dos workflows e do volume novo. Guarde cópias fora do repositório; não compartilhe prints contendo valores.
2. Atualize os arquivos do GitHub sem substituir nenhum `.env` privado.
3. Revise a diferença entre `deploy/n8n-migrado.compose.yaml` e o Compose privado; copie o novo template para a pasta privada apenas depois de preservar o anterior. Não execute `down -v`.
4. Inicie os serviços na ordem documentada e valide `python scripts/validar_execucao.py`.
5. Teste separadamente a coleta manual do workflow 01 (`failed=0`). A troca do JSON `workflows/` no disco não atualiza automaticamente os fluxos importados pelo n8n.

O esquema SQL em `db/init.sql` só é aplicado automaticamente no primeiro boot de um volume novo; alterações posteriores exigem migração SQL versionada.

## Erros comuns

| Sintoma | Diagnóstico |
|---|---|
| `localhost:5679` indisponível | Verifique `docker compose -f "$pasta\compose.yaml" ps` e os logs do n8n migrado |
| `localhost:8080` indisponível | Garanta a ordem db/api → n8n novo → web; confirme resolução `ubs-n8n-novo` no Nginx |
| HTTP 500 em `/internal/reindex` | Confirme `/app/sources.json` e o bind mount atual da API; já ocorreu falha por caminho antigo |
| `POST /api/chat` falha | Verifique workflow 02 publicado no n8n novo e conectividade com `api:8000` |
| Coleta automática duplicada | Mantenha workflow 01 legado despublicado e n8n antigo desligado |
| `Mismatching encryption keys` | Não regenere a chave nova; restaure seu `.env` privado correspondente ao volume SQLite |
| Docker não inicia | Confirme WSL 2, Docker Desktop, redes e volumes externos |

## Testes

```powershell
python -m pip install -r api/requirements-dev.txt
python -m pytest -q tests/
python -m compileall -q api/app scripts
docker compose config
# Arquivo privado: docker compose -f "$pasta\compose.yaml" config --quiet
```

A automação GitHub Actions cobre testes unitários e estrutura. A validação integrada do n8n, Nginx, banco e coleta exige executar o Compose localmente.

## Demonstrar a execução completa

Para registrar um relatório reproduzível de consultas reais (HTTP através de Nginx, webhook n8n 02, API e PostgreSQL), confira [Demonstração e evidências](DEMONSTRACAO.md) e execute a partir da raiz:

    python scripts/validar_execucao.py

Após publicar os workflows e executar a ingestão, os resultados aparecerão em artifacts/execucao-real.json e artifacts/execucao-real.md. Esses arquivos não são incluídos no Git, e qualquer cenário reprovado permanece identificado como FALHOU.

A execução manual do workflow n8n 01 deve ser confirmada separadamente nas execuções do próprio n8n. Testes de FastAPI + PostgreSQL no CI não comprovam o agendamento n8n ou a coleta de páginas públicas.

## Recuperação após regenerar .env em volumes existentes

Se o `.env` for recriado com novos segredos, os volumes PostgreSQL e o n8n legado **não** passam a usar automaticamente as novas credenciais. Podem ocorrer dois sintomas diferentes:

- FastAPI com `unhealthy` e erro PostgreSQL `password authentication failed`: o usuário do banco ainda possui a senha anterior. É necessário reconciliar a senha com um procedimento autorizado e verificado, sem expor credenciais.
- n8n reiniciando com `Mismatching encryption keys`: o segredo `N8N_ENCRYPTION_KEY` no ambiente não corresponde ao segredo da instalação persistida. Restaurar a configuração originalmente usada a partir de backup confiável, sem publicar a chave. Não alterar ou substituir arbitrariamente a chave, pois credenciais criptografadas podem ficar ilegíveis.

Diagnostique com `docker compose ps -a`, `docker compose logs --tail=80 api` e os logs do Compose **privado** do n8n migrado. Proteja a saída dos comandos: arquivos de configuração e variáveis de ambiente podem conter segredos.

**Não use `docker compose down -v` para corrigir essas falhas.** Se houver exposição de chave de criptografia, considere-a comprometida: preserve backup, planeje a reconfiguração ou rotação das credenciais e utilize procedimento suportado pela versão instalada do n8n. Nunca cole a chave no GitHub, em issues, screenshots ou logs públicos.

## Segurança e credenciais

Consulte [Segurança das credenciais](SEGURANCA_CREDENCIAIS.md) para auditoria segura, backups e plano de migração da chave de criptografia do n8n que apareceu em diagnóstico. Execute `python scripts/auditar_segredos.py` para conferir a configuração local **sem exibir segredos**. Não modifique a chave mestra de uma instância existente por substituição simples do arquivo `.env`.

## Privacidade e limites

Não inserir nomes, documentos, cartões SUS, diagnósticos ou dados clínicos no chat. O protótipo não é destinado a atender cidadãos pela internet sem revisão de segurança e governança. O horário da última verificação não demonstra que uma unidade esteja aberta neste momento; dados críticos devem ser confirmados diretamente na fonte oficial.
