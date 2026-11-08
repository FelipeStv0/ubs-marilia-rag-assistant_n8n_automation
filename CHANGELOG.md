# Histórico de alterações

## Correção de relevância e auditoria dos relatórios reais — 2026-11-08

- Recebidos e auditados JSON e Markdown da execução local, com timestamps, respostas e URLs oficiais.
- Diferenciados quatro PASSOU técnicos de três cenários semanticamente adequados e uma resposta irrelevante (endereço respondeu horário).
- Introduzida abstenção para perguntas de endereço sem evidência de logradouro próxima à unidade.
- Fortalecido o smoke test com verificação mínima de relevância e novos testes de regressão.
- Publicado resumo auditável com resultados e limites, sem expor segredos ou dados de pacientes.
- Pendente reexecutar o teste ponta a ponta após atualizar a instalação local.

## Registro de execução local e publicação segura — 2026-11-08

- Documentado o resultado observado de 6 fontes processadas (1 atualizada, 5 inalteradas, 0 falhas, 92 trechos reportados).
- Registrados quatro cenários reais de consulta com HTTP 200 e resultado agregado PASSOU no teste local.
- Separadas evidências visíveis em capturas das respostas e URLs completas, indisponíveis para auditoria nesta revisão.
- Adicionado gerador de resumo sanitizado local e testes para impedir vazamento de respostas no relatório resumido.
- Incluído procedimento de diagnóstico para inconsistência de senhas persistidas do PostgreSQL e de chave de criptografia do n8n.
- Mantido o aviso de modo extrativo sem LLM ativa, sem afiliacão institucional e sem garantia de vigência das fontes.

## Melhoria de evidências e integração — 2026-11-08

### Adicionado
- Teste de integração FastAPI com PostgreSQL/pgvector real no CI (dados sintéticos, sem n8n).
- Testes de contrato estático para endpoints e caminhos dos workflows n8n.
- Relatórios JUnit XML anexados aos jobs do GitHub Actions.
- Script de demonstração local com perguntas reais, respostas recebidas, referências, latências e falhas controladas.
- Guia de demonstração com critérios de aceitação, limitações e instruções para obter evidências reais.
- Metadados de status de coleta por fonte nas respostas e aviso visual quando a última tentativa falhou.

### Limitações mantidas
- LLM/embeddings não ativados no modo atual.
- CI não valida publicação do n8n, sites públicos ou execução de ponta a ponta.
- O script local precisa ser executado sobre a instalação efetiva para produzir resultados auditáveis.

## Versão de revisão técnica — 2026-11-08

### Atualizado
- Documentação integral de arquitetura, instalação, operação, limites e segurança.
- Comunicação explícita do estado de testes: **sem chave de API externa paga**, com busca lexical e trechos oficiais.
- Correspondência por nome de UBS/USF mais restrita, para reduzir referências a unidades incorretas.
- Validação formal de IDs, URLs, categorias, prioridades e datas das fontes autorizadas.
- Verificação de redirects e controle de tamanho do HTML durante a transferência.
- Interface informa o modo de operação retornado pelo backend.

### Adicionado
- Testes de validação de fontes e modo extrativo.
- Integração contínua no GitHub Actions.
- Regras de quebra de linhas e contexto de build Docker.
- Guias em `docs/ARQUITETURA.md` e `docs/OPERACAO.md`.

### Pendente
- Testes de integração em Docker com banco e n8n.
- Gestão estruturada de conflitos de fontes e datas de vigência.
- Procedimento de backup e restauração validado em ambiente separado.

## Versão inicial

- Ambiente Docker Compose com n8n, FastAPI, PostgreSQL/pgvector e Nginx.
- Workflows para coleta agendada e atendimento.
- Busca textual sem LLM e caminho opcional para embeddings e geração.
