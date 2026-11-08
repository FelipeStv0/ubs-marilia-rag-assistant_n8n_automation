# Segurança das credenciais e recuperação controlada

> Instalação local com Docker Compose e n8n 2.46.5. **Este procedimento não rotaciona chaves automaticamente.** A chave `N8N_ENCRYPTION_KEY` já apareceu em uma captura de diagnóstico e deve ser considerada **potencialmente comprometida**, mesmo com o ambiente restrito a `127.0.0.1`.

## Resposta imediata: o que já está protegido

- `.env` não é versionado (`.gitignore`). Os serviços web e n8n escutam somente no loopback local, segundo o Compose do repositório.
- O modo padrão está sem LLM externa, com `OPENAI_API_KEY` vazia.
- Credenciais armazenadas pelo n8n podem continuar criptografadas no PostgreSQL, mas a **exposição da chave mestra reduz a proteção** se alguém também obtiver acesso aos dados criptografados.
- Arquivos de backup, relatórios de execução e logs também podem carregar informações sensíveis; nunca os publique diretamente.

## Auditoria local sem mostrar segredos

Abra o PowerShell na raiz do projeto e execute:

```powershell
python scripts/auditar_segredos.py
```

O comando **apenas lê** o `.env` para verificar presença/comprimento dos segredos, a ausência esperada de chave paga de IA, o `.gitignore`, os binds locais e eventuais caminhos sensíveis rastreados pelo Git. Ele **não imprime valores**, não verifica a senha real do PostgreSQL, não confirma que a chave não foi exposta e não reinicia contêineres. Em um ZIP sem `.git`, não consegue auditar o histórico do Git.

Não envie seu `.env`, `docker compose config`, `docker inspect`, chaves ou prints com essas saídas a terceiros. Se precisar de suporte, forneça somente indicadores OK/WARN/FAIL e descrições sem segredos.

## Backup antes de qualquer troca de credencial

1. Faça um backup privado do `.env` atual. Trate-o como um arquivo contendo senhas, não como documentação.
2. Preserve `artifacts/` apenas em armazenamento confiável.
3. Faça uma cópia consistente do banco PostgreSQL com `pg_dump`. **A saída contém dados sensíveis; mantenha-a privada e teste a restauração em ambiente isolado.** Exemplo executado na pasta do projeto:

```powershell
New-Item -ItemType Directory -Force -Path .\backup-privado | Out-Null
docker compose exec -T db pg_dump -U automacao -d automacao -Fc -f /tmp/automacao.backup
docker compose cp db:/tmp/automacao.backup .\backup-privado\automacao.backup
docker compose exec -T db rm -f /tmp/automacao.backup
```

4. Faça backup do volume `n8n_data` e da configuração persistente do n8n com procedimento controlado; verifique consistência e possibilidade de restauração.
5. **Não use `docker compose down -v`** e não remova volumes no Docker Desktop. Não exclua a instalação anterior antes de validar os backups.
6. A pasta `backup-privado/` é ignorada pelo Git. Evite sincronizá-la automaticamente com pastas públicas.

## Diferença entre a chave mestra e a chave de dados

O n8n possui dois conceitos distintos:

- **`N8N_ENCRYPTION_KEY` (chave mestra da instância):** no n8n 2.x ela deve permanecer coerente com a configuração persistida. **Não basta editar esse valor no `.env`**; isso pode impedir a leitura de credenciais antigas.
- **Data Encryption Key (chave de dados):** o n8n 2.46.5 oferece **rotação opcional** dessas chaves. Para ativar, a documentação oficial exige `N8N_ENV_FEAT_ENCRYPTION_KEY_ROTATION=true`, reinício e depois `Settings > Data Encryption Keys > Rotate key`. A chave mestra **permanece a mesma**. Essa operação não revoga a chave mestra anteriormente exposta.

Antes de habilitar essa funcionalidade, **faça backup completo e teste em cópia isolada**. Não ative a flag automaticamente em um ambiente que já usa credenciais; alguns formatos criptografados podem tornar-se incompatíveis com versões antigas do n8n, e voltar a uma versão anterior pode impedir a leitura dos dados.

Documentação oficial: https://docs.n8n.io/deploy/host-n8n/configure-n8n/security/rotate-encryption-keys

## Plano recomendado para uma chave mestra exposta

1. **Inventarie as credenciais realmente utilizadas.** Os dois workflows fornecidos ao projeto normalmente chamam endpoints internos sem API de IA paga; confirme na sua instância se foram adicionadas credenciais, tokens ou integrações. Não exporte segredos em texto claro.
2. **Se não houver credenciais reais salvas no n8n**, a opção mais simples para revogar a chave mestra exposta é criar uma **instância nova e isolada** com chave mestra nova, mantendo a instância antiga intacta até confirmar importação/publicação dos workflows e dados necessários. Não sobrescreva o banco/volume existente durante essa operação. Arquivos `workflows/*.json` não carregam, por si, os dados sensíveis dos registros de credenciais do n8n.
3. **Se houver credenciais reais**, reemita/revogue essas credenciais na origem (tokens, senhas, OAuth quando aplicável), depois reconfigure-as na nova instância. A simples rotação da chave de dados não substitui a renovação das credenciais potencialmente expostas.
4. Faça backup e teste o novo ambiente por completo (PostgreSQL, n8n, Nginx, FastAPI, atualização de fontes e consultas) antes de desativar o antigo. Não publique portas externas.
5. Registre a migração sem incluir valores secretos.

**Não efetue rotação da senha PostgreSQL apenas alterando `POSTGRES_PASSWORD` no `.env`.** A senha gravada no banco durante a inicialização persiste em seus volumes; API e n8n precisam compartilhar a credencial efetiva. Uma mudança real exige procedimento coordenado, backup, verificação de autenticação e janela de manutenção.

## Higiene adicional

- Mantenha o Docker Desktop e as imagens do projeto atualizados após avaliar compatibilidade; não atualize n8n às cegas, principalmente ao ativar rotação de chave de dados.
- Mantenha conta proprietária do n8n protegida com uma senha forte e não reutilizada.
- Evite salvar `.env` e backups em pastas sincronizadas ou compartilhadas sem proteção apropriada.
- Não copie conteúdo de `N8N_ENCRYPTION_KEY` em screenshots, issues, chats, logs ou no README.
- **Para publicação externa/produção:** exigem-se autenticação, TLS, controle de acesso, segregação de segredos, revisão LGPD e observabilidade. A presente instalação é apenas local.

## Referências oficiais

- [n8n — Rotação de chaves de criptografia](https://docs.n8n.io/deploy/host-n8n/configure-n8n/security/rotate-encryption-keys)
- [n8n — Configuração da chave da instância](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/configuration-examples/set-a-custom-encryption-key)
- [Docker — Compose Secrets](https://docs.docker.com/compose/how-tos/use-secrets)

**Estado:** medidas preventivas podem ser aplicadas no repositório agora. **A chave mestra exposta só será substituída efetivamente quando a migração local controlada for realizada.**
