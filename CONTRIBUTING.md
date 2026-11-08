# Guia de contribuição

## Fluxo de desenvolvimento

1. Crie uma branch descritiva (`feat/...`, `fix/...`, `docs/...`).
2. Faça mudanças pequenas e focalizadas; evite alterações simultâneas no modelo de dados sem migração.
3. Inclua ou ajuste testes para mudanças de comportamento.
4. Execute:
   ```bash
   python -m pip install -r api/requirements-dev.txt
   python -m pytest -q tests
   python -m compileall -q api/app scripts
   ```
5. Abra um pull request descrevendo o motivo, os testes realizados e os riscos.

## Requisitos de qualidade

- Não adicionar fontes fora dos domínios municipais e federais autorizados sem revisão.
- Não inserir dados pessoais ou informações clínicas de cidadãos em testes, fixtures ou exemplos.
- Não enviar `.env`, tokens, segredos, dumps de banco ou credenciais do n8n.
- Todo resultado sobre horário, documento ou endereço deve manter referência à fonte.
- O modo de testes sem LLM não deve sintetizar fatos ou apresentar trechos como respostas validadas.
- Não alterar nomes de branches, portas ou configurações de serviços sem atualizar a documentação.

## Classificação de mudanças

- **feat:** nova funcionalidade.
- **fix:** correção de comportamento.
- **refactor:** melhoria de código sem mudança de contrato.
- **test:** novos testes.
- **docs:** documentação.
- **chore:** manutenção de infraestrutura e ferramentas.

## Escopo

Este projeto não aceita funções de diagnóstico, classificação de gravidade, prescrição ou consulta de prontuários no protótipo administrativo atual.
