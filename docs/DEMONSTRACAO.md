# Demonstração reproduzível e evidências de execução

## Estado e escopo

Este repositório é um protótipo acadêmico independente. **A LLM está desativada** (OPENAI_API_KEY vazia). O funcionamento atual é de **recuperação lexical extrativa**: a API devolve um trecho indexado, seu link e metadados de coleta. Não gera síntese por LLM, não oferece aconselhamento clínico e não confirma a vigência de horários ou serviços.

**Não confundir os níveis de teste:**

| Evidência | O que comprova | O que NÃO comprova |
|---|---|---|
| Unitários (CI) | Regras isoladas de coleta, configuração, busca e segurança | Conexão com serviços reais |
| Contratos dos workflows (CI) | Estrutura e URLs declaradas em JSON/n8n/Nginx | Workflow publicado ou executado |
| Integração FastAPI + PostgreSQL (CI) | Rotas HTTP in-process consultando PostgreSQL/pgvector real, erros de ingestão e retenção de dados | n8n, Nginx, coleta HTTP de sites oficiais |
| Smoke test local | HTTP Nginx → webhook de produção n8n 02 → FastAPI → PostgreSQL, com respostas realmente recebidas | Agendamento n8n 01 ou atualidade das fontes |
| Execução manual n8n 01 | Trigger e reindexação na instância local, quando documentados por logs | Prova permanente de vigência das páginas |

Os textos usados no CI são **fixtures sintéticas** e não representam informação sobre unidades reais. Os testes de perguntas reais só adquirem evidência quando executados contra uma instalação local com dados coletados.

## Preparar ambiente e workflows

No PowerShell, dentro do diretório do projeto:

    python scripts/gerar_env.py
    docker compose up -d --build
    docker compose ps

Verifique que OPENAI_API_KEY está vazia no arquivo .env local (não versionado). Acesse http://localhost:5678, importe os dois arquivos da pasta workflows e publique ambos. Depois, execute manualmente o workflow 01 (atualização de fontes) e registre no n8n o horário, os nós concluídos e o resultado retornado por /internal/reindex. **Esse passo não é disparado nem validado pelo script abaixo.**

Alternativamente, é possível testar a rotina de coleta via API Docker:

    docker compose exec -T api python -m app.bootstrap

Esse comando testa a coleta pelo backend, **não** o agendamento do workflow 01 no n8n.

## Capturar execução real de perguntas e respostas

Com o workflow 02 publicado e a base preenchida:

    python scripts/validar_execucao.py

Ou, para solicitar também uma coleta via API antes das perguntas:

    python scripts/validar_execucao.py --coletar

O script registra em artifacts/execucao-real.json e artifacts/execucao-real.md: data e horário UTC, HTTP status, latência, pergunta enviada, resposta retornada, modo, suficiência, títulos/URLs, data da última coleta bem-sucedida e estado da fonte. Ao final, apresenta PASSOU ou FALHOU por cenário; sai com código 1 quando algum requisito não é atendido. **Os arquivos só existem depois da execução local** e não estão incluídos neste repositório.

Os artefatos são ignorados pelo Git para evitar publicação acidental de dados coletados. Revise o conteúdo antes de compartilhar e nunca inclua dados de pacientes, credenciais ou segredos.

## Cenários end-to-end e resultados esperados

| ID | Pergunta ou ação | Resultado exigido |
|---|---|---|
| endereco_ubs | Onde fica a UBS Castelo Branco? | HTTP 200, modo extractive, trecho textual e ao menos uma URL oficial com data de coleta |
| documentos_vacina | Quais documentos devo levar para vacinação? | HTTP 200, modo extractive, trecho textual e ao menos uma fonte oficial |
| unidade_inexistente | Qual o endereço da UBS Inexistente Arco Iris 999? | HTTP 200, modo no_evidence, abstenção e nenhuma fonte atribuída |
| emergencia | Estou com dor no peito | HTTP 200, modo safety, encaminhamento ao SAMU 192, sem diagnóstico nem citação falsa |
| metodo_bloqueado | GET /api/chat | HTTP 403 pelo Nginx |
| estado_da_base | GET /api/status | 200, rag_mode extractive_lexical, fontes com sucesso e trechos ativos |

Estes são **critérios de aceitação**. Uma execução local anterior está documentada, mas detectou uma resposta de horário para pergunta de endereço. Veja [auditoria real](AUDITORIA_RESPOSTAS_REAIS_2026-11-08.md). Se o coletor não obtiver evidência oficial para uma das perguntas, o cenário falhará e o relatório preservará a resposta realmente obtida. Um relatório com falhas é útil como diagnóstico; não deve ser rotulado como validação bem-sucedida.

Exemplo de formato esperado do endpoint (valores abaixo são **ilustrativos**, não saída observada):

    {
      "mode": "extractive",
      "sufficient": true,
      "answer": "Modo de testes — sem API de IA. Trecho localizado ...",
      "sources": [
        {
          "title": "Título retornado pela base",
          "url": "https://www.marilia.sp.gov.br/...",
          "checked_at": "<timestamp real da última coleta>",
          "source_status": "ok"
        }
      ]
    }

Os campos efetivos devem ser obtidos nos arquivos da pasta artifacts. O programa nunca deve preencher a saída real com respostas simuladas.

## Execução local documentada (08/11/2026)

Foi apresentada evidência de execução do workflow 01, com 6 fontes, 1 atualizada, 5 inalteradas, 0 falhas e 92 trechos somados, além de um smoke test do workflow 02 com os quatro cenários aprovados e resultado agregado PASSOU.

Veja [Evidências observadas da execução](EVIDENCIAS_EXECUCAO_2026-11-08.md) para os valores registrados e as limitações. Essa síntese é baseada em capturas e **não substitui** os arquivos `artifacts/execucao-real.json` e `artifacts/execucao-real.md` efetivamente produzidos no computador local. Não foi possível verificar o texto integral de respostas, seus links ou timestamps.

### Gerar um resumo sanitizado

Depois de executar o smoke test:

```powershell
python scripts/resumir_evidencias.py
```

Isso gera `artifacts/resumo-publicavel.md`, contendo somente cenários, códigos HTTP, modos e quantidades de fontes. O script verifica a estrutura do JSON, não valida a veracidade de informações extraídas. Revise manualmente antes de publicar. Os artefatos continuam excluídos do Git por padrão.

## Verificação de relevância — correção da revisão de 08/11/2026

Os arquivos reais mostraram uma falha importante: HTTP 200, `extractive` e link oficial não bastam para assegurar que a resposta atende à pergunta. O teste `endereco_ubs` retornou horário estendido e não endereço. A partir desta revisão, o backend busca evidência de logradouro junto ao nome da unidade para perguntas de localização; na falta dessa evidência, **abstém-se**. O script `validar_execucao.py` também aplica verificação mínima de relevância para endereço e documentos. Não confundir essa heurística com verificação factual ou geocodificação.

A evidência histórica está em [Auditoria das respostas reais](AUDITORIA_RESPOSTAS_REAIS_2026-11-08.md). **Não apresentar a antiga execução como 4/4 respostas semanticamente corretas.** Depois de atualizar o código local, execute o script novamente para avaliar a correção no sistema real.

## Falhas controladas

1. **Pergunta sem evidências:** a busca deve retornar no_evidence, sufficient=false e lista de fontes vazia, sem atribuir dados de outra UBS.
2. **Situação de emergência:** o serviço retorna uma orientação de segurança genérica, sem triagem nem citações fabricadas; o conteúdo não substitui atendimento médico.
3. **Formato inválido:** o teste de integração FastAPI verifica HTTP 422 quando a pergunta possui menos de quatro caracteres. A validação passa pela API diretamente, não pelo webhook do n8n.
4. **Falha de coleta:** o teste de integração simula timeout HTTP. Confirma que a fonte muda para status=error, o último sucesso é mantido e os trechos já indexados não são apagados. Respostas obtidas de fonte nessa condição incluem source_status=error e a interface mostra aviso de desatualização potencial.
5. **Método HTTP não permitido:** GET /api/chat deve ser bloqueado pelo Nginx com 403.

A quarta falha é **injetada em teste**; não foi provocada em serviço oficial. Nenhuma LLM é chamada nesses testes.

## Resultado dos testes no GitHub Actions

A pipeline tem dois jobs independentes:

- unit-and-contract: executa testes unitários, verifica contratos dos arquivos n8n, sintaxe Python, JSON e padrões de segredos; gera o artefato unit-test-results.
- fastapi-postgres-integration: sobe um serviço PostgreSQL real com pgvector, aplica db/init.sql e executa os testes de integração; gera fastapi-postgres-integration-results.

Veja a página Actions do repositório e confira o commit e os resultados de ambos os jobs. Os relatórios JUnit XML permanecem disponíveis como artefatos da execução conforme retenção do GitHub.

**CI verde prova somente o que seus jobs executaram.** Não comprova coleta bem-sucedida de URLs reais, workflow n8n publicado em instância local nem execução real do frontend. Para essa etapa, execute o script localmente e preserve os artefatos correspondentes.

## Evidências complementares para apresentação

Documente a execução manual do workflow 01 no editor do n8n (tela de execuções e nós), o dashboard de fontes ou resposta do status, e a saída de perguntas reais do relatório local. Registre horário, commit Git, configuração de ambiente sem segredos, versões das imagens e URLs oficiais consultadas. Verifique as páginas originais antes de afirmar endereço, vacinação ou horário como informação vigente.

O projeto não é afiliado à Prefeitura de Marília e não deve ser exposto publicamente sem revisão de segurança, LGPD, governança e operação.
