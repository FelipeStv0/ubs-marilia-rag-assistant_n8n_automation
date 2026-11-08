# Assistente de UBS e USF — Marília/SP (n8n + RAG)

Projeto completo para execução local com Docker Compose. Atualiza uma base de conhecimento exclusivamente com páginas oficiais autorizadas e atende perguntas com recuperação de trechos e, opcionalmente, geração de respostas por IA.

> **Protótipo acadêmico independente.** Não é um serviço oficial da Prefeitura. Não realiza diagnóstico, triagem clínica ou agendamento. Não solicite dados pessoais de saúde. Antes de publicar na internet, implemente HTTPS, autenticação/observabilidade adequada, revisão de segurança e validação institucional.

## Componentes

| Componente | Endereço local | Uso |
|---|---|---|
| n8n | http://localhost:5678 | Editor e execução dos workflows |
| Chat web | http://localhost:8080 | Interface do cidadão |
| API FastAPI | rede Docker interna | Coleta, banco, recuperação e geração |
| PostgreSQL + pgvector | rede Docker interna | Fontes, versões, trechos e embeddings |

## Instalação no Windows (Docker Desktop)

1. Instale e inicie **Docker Desktop** (com WSL2) e **Python 3**.
2. Extraia o ZIP. Abra PowerShell na pasta `assistente_ubs_marilia_n8n`.
3. Execute `python scripts/gerar_env.py`. Isso gera senhas aleatórias e o arquivo `.env`.
4. Abra `.env` no Bloco de Notas. Preencha `OPENAI_API_KEY=...` com sua chave **se quiser respostas generativas e busca vetorial**. A chave não está incluída neste projeto e pode gerar custos na API. Sem a chave, a busca lexical funciona e mostra o trecho oficial encontrado, mas não gera uma resposta por LLM.
5. Execute `docker compose up -d --build`.
6. Abra **http://localhost:5678** e crie a conta proprietária local do n8n.
7. Execute `python scripts/instalar_workflows.py`. O script importa os dois JSON, tenta publicá-los e faz a coleta inicial.
8. Abra **http://localhost:8080** e envie uma pergunta.

Alternativamente, execute `powershell -ExecutionPolicy Bypass -File scripts/iniciar_windows.ps1` a partir da pasta do projeto. O script guia a etapa de criação da conta no n8n.

### Instalação manual (se o script de publicação falhar)

No n8n, use **Import from File** para importar individualmente:
- `workflows/01-atualizacao-fontes.json`
- `workflows/02-perguntas-rag.json`

Abra cada workflow e clique **Publish**. Depois, no terminal, execute:

```powershell
docker compose exec -T api python -m app.bootstrap
```

Os webhooks de produção só são registrados após publicar. A versão n8n 2.x utiliza o modelo de **publicação** em vez do antigo toggle de ativação.

## O que foi implementado

**Workflow 01 — Atualização**
- `Schedule Trigger` executa a cada **6 horas** (editável no node).
- `Manual Trigger` permite executar imediatamente no editor.
- `HTTP Request` aciona a API interna `POST /internal/reindex`.
- A API visita as URLs listadas em `sources.json`, remove elementos HTML de navegação, extrai o texto e cria trechos.
- Compara SHA-256 do conteúdo normalizado com o hash anterior. Não reprocesa páginas idênticas desnecessariamente.
- Para conteúdo alterado, versiona os trechos, gera embeddings (se houver chave válida) e registra a revisão no banco; preserva versões anteriores para auditoria.
- Falhas de uma fonte não apagam os trechos anteriores; são registradas nas tabelas `ubs.sources` e `ubs.ingestion_runs`.

**Workflow 02 — Chat**
- Webhook `POST /webhook/ubs-marilia` recebe `{ "question": "..." }`.
- `HTTP Request` aciona a API interna `/internal/answer`.
- A API faz busca lexical com PostgreSQL FTS + trigramas e, com chave OpenAI, também busca vetorial usando pgvector.
- A IA recebe os trechos e produz JSON com `answer`, `used_source_ids` e `sufficient`. Somente IDs realmente recuperados são aceitos na resposta.
- Sem evidência suficiente, retorna uma mensagem de abstenção. O chat mostra links, trechos e datas de verificação.

**Interface**
- Frontend estático responsivo em HTML/CSS/JS, servido por Nginx.
- Nginx usa proxy para o webhook do n8n, evitando problemas de CORS, e limita requisições de chat.
- Exibe referências oficiais clicáveis e o estado da indexação.

## Fontes e diferenças nos horários

As seis fontes iniciais de `sources.json` incluem o catálogo municipal de unidades, a notícia municipal sobre horário ampliado, a campanha municipal de multivacinação, páginas do Ministério da Saúde e a orientação municipal sobre urgências. Só URLs da lista são coletadas. **Nenhuma busca geral na web é feita em tempo de atendimento.**

O catálogo geral da Prefeitura apresenta alguns horários antigos, enquanto a publicação de setembro de 2026 informa ampliação para unidades específicas. O prompt instrui a IA a conferir datas e explicitar incertezas quando necessário. Essa é uma **mitigação**, não uma garantia de detecção automática de toda divergência. Recomenda-se revisão humana de horários conflitantes antes de uso público.

Para incluir outra página oficial, edite `sources.json` e execute a coleta. O sistema limita os domínios permitidos a `www.marilia.sp.gov.br`, `saude.marilia.sp.gov.br` e `www.gov.br`; alterações dessa lista exigem alteração deliberada em `api/app/config.py`.

## Testar a API por meio do webhook

```powershell
curl.exe -X POST http://localhost:5678/webhook/ubs-marilia -H "Content-Type: application/json" -d '{"question":"Qual é o horário da UBS Nova Marília?"}'
```

Se ocorrer erro por causa das aspas do PowerShell, use o chat web em `http://localhost:8080` para o teste inicial.

Para reiniciar coleta manual:

```powershell
docker compose exec -T api python -m app.bootstrap
```

Para inspecionar logs:

```powershell
docker compose logs -f api n8n
docker compose ps
```

Para ver o status do índice, visite `http://localhost:8080/api/status`.

## Organização dos arquivos

```text
assistente_ubs_marilia_n8n/
├── docker-compose.yml
├── .env.example
├── sources.json
├── db/init.sql
├── workflows/
│   ├── 01-atualizacao-fontes.json
│   └── 02-perguntas-rag.json
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/{main,collector,rag,llm,config,db,bootstrap}.py
├── nginx/default.conf
├── web/{index.html,styles.css,app.js}
├── scripts/{gerar_env,instalar_workflows}.py
└── tests/test_collector.py
```

## Restrições e próximos cuidados

- Precisa de Docker Desktop. Não há credencial de API OpenAI embutida; usá-la pode gerar custos. Modo sem chave é limitado à recuperação textual.
- As fontes são **HTML**. PDFs, páginas carregadas exclusivamente por JavaScript, conteúdo protegido por CAPTCHA e varredura automática de links não estão implementados.
- Alguns sites podem bloquear requisições ou mudar o HTML. A plataforma registra a falha e mantém o último conteúdo, mas dados antigos não são considerados validação de disponibilidade atual.
- A coleta usa uma lista fixa; novas notícias **não entram automaticamente** sem inclusão da respectiva URL. A atualização periódica detecta mudanças **nas URLs monitoradas**, não descobre todas as novas páginas. Para descoberta automática de comunicados seria necessária uma etapa adicional de feed/sitemap com aprovação de fontes.
- O modelo de IA recebe texto de fonte externa como dados. O prompt restringe instruções maliciosas, mas é necessária validação operacional adicional contra prompt injection.
- Evite hospedar este ambiente local diretamente na Internet. No Compose, chat e n8n aceitam conexões apenas de `127.0.0.1` do computador hospedeiro.
- Nenhuma execução Docker ponta a ponta foi realizada no ambiente usado para empacotar o projeto: sintaxe e testes locais podem ser verificados, mas a integração real precisa ser validada após iniciar o Docker.

## Referências

- https://docs.n8n.io/
- https://github.com/n8n-io/n8n-docs/blob/main/docs/deploy/host-n8n/configure-n8n/use-the-command-line.md
- https://www.marilia.sp.gov.br/portal/secretarias-paginas/16/unidades-de-saude---marilia-e-regiao/
- https://saude.marilia.sp.gov.br/video/programa-mais-saude-mais-horario/17
- https://www.gov.br/saude/pt-br/vacinacao/calendario
