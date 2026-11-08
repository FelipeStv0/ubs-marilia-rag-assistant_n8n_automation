# Evidências observadas da execução local — 08/11/2026

> **Status:** validação funcional local concluída nos cenários apresentados. Evidências abaixo derivadas de capturas do painel n8n e do PowerShell, não de dumps do banco nem dos relatórios integrais da execução. **Protótipo independente, sem LLM ativa.**

## Contexto e escopo

- Ambiente: Windows PowerShell, Docker Compose, Nginx, n8n, FastAPI e PostgreSQL/pgvector, executados localmente.
- Serviço generativo: **desativado**. Consultas extrativas com busca lexical; não houve necessidade de configurar credenciais de LLM.
- Separação das evidências: o workflow 01 foi observado no n8n; as consultas do workflow 02 foram verificadas por `scripts/validar_execucao.py`; a integração FastAPI/PostgreSQL foi validada separadamente no GitHub Actions.
- Momento da observação: **08/11/2026**. O horário exato da coleta e o timestamp UTC do script não estão disponíveis nas capturas aqui analisadas.

## Workflow 01 — coleta e indexação

A execução apresentada no n8n terminou com o nó **Coletar, detectar mudanças e indexar** em estado de sucesso e retornou:

| Métrica | Resultado observado |
|---|---:|
| Fontes cadastradas/processadas | 6 |
| Fontes atualizadas | 1 |
| Fontes sem alterações detectadas | 5 |
| Falhas de coleta | 0 |
| Trechos reportados por fonte (soma) | 92 |

| Identificador da fonte | Situação na coleta | Trechos |
|---|---|---:|
| `marilia_unidades` | `unchanged` | 53 |
| `marilia_horarios_ampliados` | `unchanged` | 2 |
| `marilia_multivacinacao_2026` | `unchanged` | 4 |
| `ms_vacinacao` | `unchanged` | 7 |
| `ms_calendario` | `unchanged` | 18 |
| `marilia_urgencia` | `updated` | 8 |

**Interpretação:** seis fontes foram processadas sem erro na execução apresentada. A soma de 92 corresponde aos valores `chunks` retornados por fonte, **não** a uma contagem independente do total de registros ativos no banco. O estado `unchanged` compara o conteúdo com uma versão previamente indexada; não comprova que o dado é vigente ou correto.

## Workflow 02 — verificação local de perguntas reais

Com o workflow de atendimento publicado, o comando `python scripts/validar_execucao.py` retornou a seguinte síntese no PowerShell:

| Cenário | HTTP observado | Modo | Resultado |
|---|---:|---|---|
| `endereco_ubs` | 200 | `extractive` | PASSOU |
| `documentos_vacina` | 200 | `extractive` | PASSOU |
| `unidade_inexistente` | 200 | `no_evidence` | PASSOU |
| `emergencia` | 200 | `safety` | PASSOU |
| Verificações adicionais (status da base e método GET bloqueado) | Não discriminadas na captura | — | Incluídas no resultado agregado PASSOU do script |

Saída final observada: `RESULTADO PASSOU`. O script informou a criação de `artifacts/execucao-real.json` e `artifacts/execucao-real.md`, **no computador local**.

O fluxo coberto pelo script atravessa Nginx → webhook publicado do n8n → FastAPI → PostgreSQL, enquanto o workflow 01 de ingestão foi observado em execução separada.

**Limite de rastreabilidade:** as capturas não contêm o texto integral das respostas, as URLs individuais retornadas nas consultas, latências ou o arquivo de evidências gerado localmente. Esses dados **não são reproduzidos nem presumidos** neste repositório. Para incluí-los depois de uma revisão de privacidade, exporte um resumo sanitizado com `scripts/resumir_evidencias.py`.

## Testes automatizados disponíveis

Na execução do GitHub Actions de 08/11/2026, os jobs anteriores à coleta local registraram **16 testes unitários/contratos aprovados** e **4 testes FastAPI/PostgreSQL aprovados**. Referência: [execução do CI na branch main](https://github.com/FelipeStv0/ubs-marilia-rag-assistant_n8n_automation/actions/runs/42500150819).

Isso não equivale a confirmar que todos os serviços externos funcionarão em outras instalações.

## O que ainda não foi comprovado

- Correção factual dos endereços, documentos, horários e campanhas nas páginas originais.
- Precisão estatística do recuperador, estabilidade ao longo do tempo ou operação em produção.
- Validação clínica, segurança para dados pessoais ou conformidade de uma implantação pública.
- Execução de modelos de linguagem, embeddings pagos ou respostas generativas — **a LLM permanece desativada**.
- Os textos integrais de perguntas/respostas/URLs não podem ser publicados como se tivessem sido analisados aqui.

## Reprodutibilidade e privacidade

1. Preserve o `.env`, a chave do n8n e os volumes. **Nunca publique chaves, tokens, senhas, arquivos de configuração do n8n ou dumps.**
2. Execute a coleta no workflow 01 do n8n; anote o resultado e as datas reais.
3. Execute `python scripts/validar_execucao.py` no ambiente local.
4. Revise `artifacts/execucao-real.json` e `artifacts/execucao-real.md` antes de compartilhar qualquer trecho.
5. Para publicar uma síntese verificável sem respostas completas, utilize `python scripts/resumir_evidencias.py`. Os resultados privados continuam ignorados pelo Git.
6. Como uma chave de criptografia do n8n apareceu em uma captura de diagnóstico, trate-a como **potencialmente comprometida**. Não a divulgue novamente; planeje backup, substituição/reconfiguração de credenciais e rotação em ambiente controlado. Substituir apenas `N8N_ENCRYPTION_KEY` em uma instalação existente pode tornar credenciais inacessíveis.

**Declaração institucional:** projeto acadêmico independente; não é canal da Prefeitura de Marília nem oferece diagnóstico, triagem ou orientações médicas.
