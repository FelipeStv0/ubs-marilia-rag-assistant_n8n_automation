# Migração segura do n8n para nova chave — execução local verificada em 09/11/2026

Este documento descreve a topologia **observada no computador do operador**, e a configuração versionada que permite reconstruí-la sem publicar credenciais. Não é uma certificação de produção.

## Resultado observado

- Backup privado do PostgreSQL: `automacao.backup` com 688.042 bytes; hashes SHA-256 local e original idênticos.
- Backup dos workflows: `workflows-n8n.json`, três fluxos exportados (um deles duplicado e não publicado).
- Backup do volume antigo do n8n: `n8n_data.tar.gz`, arquivo TAR legível.
- Restauração de teste do PostgreSQL em `ubs-restore-test-db`: concluída sem erro; 3 registros em `public.workflow_entity` e 108 registros em `ubs.passages` (incluindo possíveis históricos).
- Nova instância `ubs-n8n-novo` com chave própria e SQLite no volume `ubs_n8n_nova_data`; interface em `127.0.0.1:5679`.
- Nova instância conectada à rede `assistente-ubs-marilia_private`, acessando a FastAPI por `http://api:8000` (HTTP 200).
- Nginx aponta para `http://ubs-n8n-novo:5678/webhook/ubs-marilia`; quatro cenários de atendimento passaram via `http://localhost:8080`.
- Workflow 01 no novo n8n: coleta manual de seis fontes, `updated=0`, `unchanged=6`, `failed=0`.
- Workflow 01 antigo foi despublicado; o contêiner `assistente-ubs-marilia-n8n-1` foi parado. Uma nova execução de `python scripts/validar_execucao.py` continuou com **4/4 PASSOU**.
- **Os testes confirmam os cenários apresentados, não a validade clínica ou vigência das fontes.**

## Arquitetura atual

```text
Navegador :8080
   -> Nginx (Compose principal: web)
   -> ubs-n8n-novo:5678 (Compose privado: porta host 5679)
   -> api:8000 (FastAPI, Compose principal)
   -> PostgreSQL (Compose principal)
Fontes oficiais -> workflow 01 no n8n novo -> api:/internal/reindex
```

O n8n novo **não usa o PostgreSQL antigo para suas próprias tabelas**, mas utiliza a FastAPI desse projeto para consultar os dados administrativos armazenados no PostgreSQL.

### O que é versionado, e o que permanece privado

| Item | Local | Git |
|---|---|---|
| Compose principal sem n8n antigo | `docker-compose.yml` | Sim |
| Template do n8n novo, sem segredos | `deploy/n8n-migrado.compose.yaml` | Sim |
| Arquivo do Nginx apontando para n8n novo | `nginx/default.conf` | Sim |
| Compose privado, copiado do template | `$HOME\Documents\UBS-Backup\migracao-n8n\compose.yaml` | Não |
| Nova chave de criptografia | `$HOME\Documents\UBS-Backup\migracao-n8n\.env` | **Nunca** |
| Dados da nova instância | Volume `ubs_n8n_nova_data` | Não |
| Backup da instância antiga | `$HOME\Documents\UBS-Backup` e volume antigo | Não |

**Não publique arquivos `.env`, dumps, arquivos `.tar.gz` do n8n, capturas de valores secretos ou exportações integrais de credenciais.**

## Provisionar em um computador novo (sem volumes anteriores)

Se não existe instalação anterior, gere o `.env` do PostgreSQL com `python scripts/gerar_env.py` antes de criar volumes. Depois execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\preparar_n8n_migrado.ps1
```

O script gera chave aleatória para o n8n novo somente se não houver `.env` nem volume `ubs_n8n_nova_data`. **Se o volume existir sem a chave, aborta deliberadamente** para impedir perda de acesso ao SQLite. Não imprime a chave. Depois siga a ordem de inicialização e importe os workflows pelo editor `http://localhost:5679`, mantendo apenas um fluxo de coleta agendado.

## Atualizar a configuração local sem substituir a chave

Execute no PowerShell dentro da pasta do projeto atualizado. **Antes de substituir os arquivos**, preserve o `.env` original e o `.env` PRIVADO da nova instância, em locais diferentes.

```powershell
$pasta = "$HOME\Documents\UBS-Backup\migracao-n8n"
Test-Path "$pasta\.env"
Test-Path "$pasta\compose.yaml"
docker volume inspect ubs_n8n_nova_data --format '{{.Name}}'
docker network inspect assistente-ubs-marilia_private --format '{{.Name}}'
```

Não compartilhe o conteúdo dos arquivos privados. Os comandos de inspeção devem retornar presença de ambos os recursos Docker. **Não gere uma chave nova para uma instância cujo SQLite já contém workflows e credenciais.** Preserve a chave nova criada durante a migração.

O template versionado pode ser copiado para substituir **somente** o Compose privado (faça backup do Compose existente antes). Não copie `.env` junto, pois o template não o contém:

```powershell
Copy-Item "$pasta\compose.yaml" "$pasta\compose.yaml.backup" -Force
Copy-Item .\deploy\n8n-migrado.compose.yaml "$pasta\compose.yaml" -Force
docker compose -f "$pasta\compose.yaml" config --quiet
```

A atualização pode alterar o contêiner **somente quando você executar `up`**. Preserve o SQLite e os backups do volume antes de qualquer recriação.

## Inicialização segura (ordem obrigatória)

O Nginx resolve `ubs-n8n-novo` pela rede Docker. Se o Compose principal iniciar o web antes de o n8n novo existir na rede, o Nginx pode falhar ao inicializar. A ordem recomendada é:

```powershell
# Na pasta do projeto, com .env do PostgreSQL original preservado
$pasta = "$HOME\Documents\UBS-Backup\migracao-n8n"
docker compose up -d --build db api
docker compose -f "$pasta\compose.yaml" up -d
docker compose up -d web
python scripts/validar_execucao.py
```

O atalho `powershell -ExecutionPolicy Bypass -File .\scripts\iniciar_windows.ps1` executa essa sequência, mas **se recusa a gerar novas credenciais caso o .env esteja ausente**.

- `docker compose up -d` no Compose principal **não inicia mais o n8n antigo**: ele foi removido da definição versionada.
- O contêiner antigo, já parado, pode aparecer como *orphan*. Não use `--remove-orphans` enquanto ele estiver sendo preservado.
- Não execute `docker compose down -v`; isso apagaria dados persistentes.
- Recriar a rede privada do projeto enquanto a nova instância a utiliza exige planejamento: é uma rede externa para o Compose privado.
- A rede e o volume `ubs_n8n_nova_data` são recursos preexistentes (external); sem eles, o Compose privado **deve falhar**, em vez de criar dados novos silenciosamente.

## Confirmar que apenas a coleta nova está ativa

1. No n8n novo em `http://localhost:5679`, verifique que **01 — Atualização das fontes** e **02 — Atendimento** estejam publicados.
2. No n8n antigo, preserve o workflow 01 **não publicado**. A instância antiga deve continuar parada.
3. Na coleta manual do workflow 01 novo, confirme `total=6` e `failed=0`; mudanças reais podem alterar `updated` e `unchanged`.
4. Rode `python scripts/validar_execucao.py`; espere os quatro cenários aprovados. Os critérios de relevância são heurísticos.

## Diagnóstico e recuperação

```powershell
$pasta = "$HOME\Documents\UBS-Backup\migracao-n8n"
docker compose ps -a
docker compose -f "$pasta\compose.yaml" ps
docker compose -f "$pasta\compose.yaml" logs --tail=60 n8n
docker compose exec -T web nginx -t
docker compose exec -T web getent hosts ubs-n8n-novo
docker compose exec -T api ls -l /app/sources.json
```

**Se `/app/sources.json` estiver ausente:** confirme o bind mount no `docker inspect` e recrie apenas a API a partir da pasta correta, sem tocar no banco. Essa falha já provocou HTTP 500 no endpoint `POST /internal/reindex` durante a migração.

**Se n8n novo não iniciar:** não modifique `N8N_ENCRYPTION_KEY` arbitrariamente e não apague o SQLite. Verifique o `.env` privado correto, o volume e os logs. Se o Compose apontar para uma pasta antiga, ajuste o caminho de execução antes de recriar contêineres.

**Reversão controlada:** preserve o contêiner e o volume antigos. Para voltar ao workflow 02 antigo, será preciso restaurar o proxy Nginx antigo e iniciar o contêiner antigo conscientemente; jamais publique simultaneamente as duas coletas. Faça backup e siga um roteiro de mudança com verificação do webhook antes de usar novamente o endpoint :8080. Nunca recoloque a chave antiga em artefatos públicos.

## Pendências e limites de segurança

- O backup do PostgreSQL foi restaurado em ambiente isolado, mas o volume `n8n_data.tar.gz` só teve a integridade do TAR conferida; não há evidência de restauração integral da configuração antiga do n8n.
- A nova instância não executa diagnóstico clínico, não é oficial e não está pronta para exposição à internet.
- A chave antiga continua existindo nos backups privados/volume legado, mas deixou de ser necessária ao n8n que atende o chat. Proteja e retenha esses backups conforme política local; não declare a chave antiga como apagada.
- A conta nova do n8n e o `.env` privado devem permanecer protegidos, mesmo em `127.0.0.1`.
- O arquivo Compose do n8n migrado é deliberadamente separado para não acionar acidentalmente os dados antigos.
