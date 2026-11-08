# Arquitetura e decisões técnicas

## Objetivo

Oferecer consulta a **informações administrativas públicas** de UBS e USF de Marília/SP, com rastreabilidade por URL oficial. O projeto não faz diagnóstico, triagem clínica, prescrição ou agendamento.

## Componentes e fronteiras

1. **Nginx + frontend estático**: oferece a interface e encaminha `/api/chat` ao webhook de produção do n8n. Aplica controles básicos de HTTP e limitação de taxa.
2. **n8n**: orquestra dois fluxos independentes: coleta periódica e atendimento sob demanda. Executa o gatilho, mas a lógica de extração e persistência está na API Python para facilitar testes.
3. **API FastAPI**: encapsula extração, segmentação, versionamento, recuperação híbrida e integração opcional com LLM.
4. **PostgreSQL + pgvector**: mantém fontes autorizadas, trechos ativos e históricos, hashes, logs de ingestão e embeddings opcionais.

## Ciclo de atualização

```text
Schedule Trigger (6h) ou Manual Trigger
  -> POST /internal/reindex
  -> Validação de sources.json
  -> Requisição HTTPS com host em allowlist e redirecionamento controlado
  -> HTML para texto (remoção de navegação/scripts)
  -> Chunking conforme categoria
  -> SHA-256 do conteúdo normalizado
  -> Se idêntico: registra verificação
  -> Se alterado: versão anterior inativa, nova versão ativa,
     vetores opcionais, histórico preservado
```

**Justificativas:** o hash reduz trabalho repetido; a versão inativa preserva auditoria; a lista explícita de URLs limita o risco de SSRF e de misturar fontes não autorizadas. O coletor não percorre automaticamente links encontrados nas páginas.

**Limitação:** alteração no layout do HTML pode comprometer a extração. Uma coleta malsucedida mantém os dados antigos e registra falha; essa retenção não deve ser interpretada como confirmação de atualidade.

## Ciclo de atendimento

```text
Chat -> Nginx -> webhook n8n -> POST /internal/answer
   -> identificação de termos e UBS/USF
   -> PostgreSQL FTS + similaridade de palavras
   -> (se configurado) embedding da pergunta + busca vetorial
   -> ranqueamento -> verificação de evidências
   -> sem LLM: exibição extrativa do trecho recuperado
   -> com LLM: síntese condicionada às evidências retornadas
   -> resposta + referências
```

**Por que não consultar a web a cada pergunta?** Reduz latência, custo, dependência de disponibilidade de páginas e melhora a auditabilidade dos resultados. Em contrapartida, existe atraso entre alteração externa e a próxima coleta bem-sucedida.

**Por que PostgreSQL e não apenas um vetor?** Endereços, telefones, horas e nomes de unidades exigem consultas textuais precisas. Vetores semânticos podem recuperar passagens semanticamente próximas, mas de uma unidade incorreta. Por isso a versão de testes prioriza correspondência lexical e restringe a UBS identificada.

## Fontes e conflitos

Uma página oficial não equivale necessariamente à informação vigente: podem existir páginas genéricas desatualizadas e notícias recentes informando mudança em horário. O sistema guarda URL, título, categoria, prioridade, data informada, última coleta e histórico. A priorização é heurística; ainda não existe mecanismo capaz de resolver **todos** os conflitos de vigência automaticamente.

Para uso público, implementar reconciliação de dados estruturados por unidade e categoria, revisão humana de conflito e alertas de defasagem.

## Segurança por camadas

- Fontes cadastradas: HTTPS + hosts aprovados + validação de redirecionamento.
- Nginx: limita taxa de chat, tamanho da requisição e aplica cabeçalhos.
- Banco e API: rede privada do Compose.
- n8n: porta vinculada ao loopback; credenciais cifradas pela chave definida no `.env`.
- LLM: desligada por padrão, sem chamadas externas pagas. Trechos coletados são **dados não confiáveis para instruções** quando esse modo for habilitado.

Controles adicionais para produção: autenticação, TLS, observabilidade, backup testado, revisão de dependências e políticas de proteção de dados.

## Decisões conhecidas e limites

| Decisão | Benefício | Limitação |
|---|---|---|
| Python concentra lógica | Testabilidade e separação de responsabilidades | Serviço adicional |
| Coleta agendada | Atendimento mais rápido | Janela de desatualização |
| Fontes permitidas | Restrição de origem | Exige curadoria |
| Busca lexical sem LLM | Sem custo de API de IA, respostas auditáveis | Não sintetiza nem compreende todas as paráfrases |
| Histórico imutável lógico | Auditoria e recuperação | Crescimento de armazenamento |
| Execução local | Reduz superfície de exposição | Não é infraestrutura pública |

## Dados e interface

As tabelas principais são `ubs.sources`, `ubs.passages` e `ubs.ingestion_runs`. O frontend não monta HTML a partir de respostas do usuário ou de páginas; utiliza `textContent` para reduzir risco de execução de conteúdo injetado. O chat deve ser usado apenas com informações administrativas não pessoais.
