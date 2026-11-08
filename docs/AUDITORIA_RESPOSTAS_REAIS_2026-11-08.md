# Auditoria de respostas reais — 08/11/2026

> **Ambiente:** n8n, Nginx, FastAPI e PostgreSQL locais. **Modo `extractive_lexical`, sem LLM ativa ou API de IA paga.** Os dados abaixo foram extraídos dos relatórios efetivamente fornecidos pelo operador, não simulados. Endereços e horários não foram validados independentemente com a Prefeitura.

## Metadados observados

- Gerado em: **2026-11-08T22:11:38.145281+00:00** (UTC).
- Base consultada: `http://127.0.0.1:8080` (instância local do operador).
- Fontes: **6** registradas; **6** com status `ok`, **0** com erro no momento do teste.
- Trechos ativos: **92**.
- Última coleta bem-sucedida indicada pelo status: **2026-11-08T21:00:13.384118+00:00**.
- Coleta via workflow 01: executada e documentada **separadamente** no painel n8n (6 fontes, 1 updated, 5 unchanged, 0 failed). O teste do chat não executou nova coleta.
- Verificação do status: **HTTP 200**, **93 ms**, `PASSOU`; método GET no chat: **HTTP 403**, `PASSOU`.
- Resultado geral **reportado pelo script anterior**: `PASSOU`.

## Perguntas, respostas efetivamente recebidas e avaliação crítica

| Caso | Pergunta real | Modo / HTTP | Tempo | Resposta observada (resumo fiel) | Fonte / verificação | Resultado técnico | Relevância avaliada |
|---|---|---|---:|---|---|---|---|
| `endereco_ubs` | Onde fica a UBS Castelo Branco? | `extractive` / 200 | 344 ms | Trecho informa **horário ampliado até 22h**; **não fornece endereço** | [Secretaria da Saúde de Marília — Mais Saúde, Mais Horário](https://saude.marilia.sp.gov.br/video/programa-mais-saude-mais-horario/17); coleta 21:00:10 UTC | PASSOU | **FALHOU: não responde onde fica a unidade** |
| `documentos_vacina` | Quais documentos devo levar para vacinação? | `extractive` / 200 | 110 ms | Trecho menciona **carteira de vacinação e cartão SUS ou CPF** | [Secretaria da Saúde de Marília — Multivacinação 2026](https://saude.marilia.sp.gov.br/noticias/saude---prefeitura-de-marilia-intensifica-a-campanha-de-multivacinacao-2026/817); coleta 21:00:11 UTC | PASSOU | **Adequada ao pedido**, sujeito a conferência de vigência |
| `unidade_inexistente` | Qual o endereço da UBS Inexistente Arco Iris 999? | `no_evidence` / 200 | 125 ms | Informa não haver evidência oficial suficiente; solicita confirmação com a Secretaria ou unidade | Nenhuma fonte atribuída | PASSOU | **Abstenção adequada** |
| `emergencia` | Estou com dor no peito | `safety` / 200 | 46 ms | Informa que o assistente não avalia sintomas e recomenda **SAMU 192** em caso de risco imediato | Nenhuma fonte atribuída | PASSOU | **Desvio de segurança esperado**, não validação clínica |

Os trechos apresentados são resumos da saída recebida, não citações que substituam o documento original. As fontes foram registradas com `source_status=ok`. Todas as latências são os valores do relatório local — não são benchmarks de carga.

## Não confundir disponibilidade com qualidade da resposta

**O relatório original retorna PASSOU para quatro cenários (4/4 HTTP 200)**; porém a inspeção das respostas mostra que **3/4 cenários atenderam à intenção ou ao comportamento de segurança esperado, e 1/4 falhou semanticamente**. Essa classificação manual é restrita a estes quatro exemplos; não constitui uma taxa estatisticamente representativa de precisão.

A causa observável é que a busca lexical retornou um trecho com o nome da unidade, mas que fala de horário, não de endereço. A resposta estava acompanhada por fonte oficial, porém a fonte **não sustentava a resposta à pergunta de localização**.

### Correção implementada nesta revisão

- Em perguntas explícitas de localização, o backend extrativo agora exige menção a logradouro na passagem próxima ao nome da unidade; sem isso, responde `no_evidence` em vez de afirmar `sufficient=true` para evidência irrelevante.
- O teste local passou a exigir critério mínimo de relevância por intenção para **endereço** e **documentos de vacinação**, além de HTTP 200 e referência.
- Foram acrescentados testes de regressão com dados sintéticos para reproduzir a falha e testar a correção.
- A regra é uma **heurística**, não um verificador geográfico, e não garante endereço correto nem conteúdo atualizado.

**A correção do código ainda exige uma nova execução local** com `docker compose up -d --build`, seguida por `python scripts/validar_execucao.py`. O resultado anterior permanece como evidência histórica, sem reclassificação artificial dos resultados produzidos pelo script antigo.

## Transparência e limites

- A ausência de LLM continua explícita: `extractive_lexical` usa busca lexical e extratos, não síntese generativa.
- Nenhum dado de pacientes, chave de API, senha ou segredo foi incluído neste relatório.
- Uma coleta bem-sucedida confirma que o sistema processou a página, não que o conteúdo esteja factualmente vigente.
- O CI valida código/integração de backend com dados sintéticos; não substitui o teste ponta a ponta em cada instalação.
- O projeto é independente e não representa a Prefeitura de Marília ou a Secretaria da Saúde.

