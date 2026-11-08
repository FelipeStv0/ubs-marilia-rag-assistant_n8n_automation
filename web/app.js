'use strict';
const form = document.querySelector('#chat-form');
const field = document.querySelector('#question');
const messages = document.querySelector('#messages');
const sendButton = document.querySelector('#send');

function append(tag, className, parent, content) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (typeof content === 'string') el.textContent = content;
  parent.appendChild(el);
  return el;
}

function addMessage(role, message, sources = []) {
  const wrap = append('article', `chat-message ${role}`, messages);
  append('div', 'label', wrap, role === 'user' ? 'VOCÊ' : 'ASSISTENTE · TRECHOS INDEXADOS');
  append('div', 'bubble', wrap, message);
  if (role === 'bot' && sources.length) {
    const group = append('section', 'sources', wrap);
    append('div', 'label', group, 'FONTES INDEXADAS');
    for (const src of sources) {
      let parsed;
      try { parsed = new URL(src.url); } catch { continue; }
      if (parsed.protocol !== 'https:') continue;
      const card = append('a', 'source', group);
      card.href = parsed.href;
      card.target = '_blank';
      card.rel = 'noopener noreferrer';
      append('b', '', card, src.title || 'Fonte oficial');
      if (src.excerpt) append('small', '', card, src.excerpt.slice(0, 280) + (src.excerpt.length > 280 ? '…' : ''));
      if (src.checked_at) append('small', '', card, 'Verificado em: ' + new Date(src.checked_at).toLocaleString('pt-BR'));
      if (src.source_status === 'error') append('small', 'source-warning', card, 'Atenção: a última atualização falhou. O trecho pode estar desatualizado; confira a página oficial.');
    }
  }
  messages.scrollTop = messages.scrollHeight;
  return wrap;
}

async function sendQuestion(question) {
  if (sendButton.disabled || !question || question.length > 600) return;
  const intro = messages.querySelector('.intro');
  if (intro) intro.remove();
  addMessage('user', question);
  field.value = '';
  sendButton.disabled = true;
  const loading = addMessage('bot', 'Consultando informações oficiais...');
  try {
    const response = await fetch('/api/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const data = await response.json();
    loading.remove();
    addMessage('bot', data.answer || 'Não foi possível gerar uma resposta.', data.sources || []);
  } catch {
    loading.remove();
    addMessage('bot', 'Não foi possível consultar o assistente. Confirme se os workflows estão publicados no n8n e tente novamente.');
  } finally {
    sendButton.disabled = false;
    field.focus();
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  sendQuestion(field.value.trim());
});
document.querySelectorAll('[data-question]').forEach(button => {
  button.addEventListener('click', () => sendQuestion(button.dataset.question));
});
fetch('/api/status').then(r => r.json()).then(data => {
  document.querySelector('#status').textContent = `Base: ${data.passages} trechos ativos · ${data.sources_ok}/${data.sources} fontes disponíveis`;
  document.querySelector('#rag-mode').textContent = data.rag_mode === 'llm_and_vector' ? 'Modo RAG com geração habilitado.' : 'Modo de testes: busca lexical e trechos oficiais, sem API externa paga.';
}).catch(() => { document.querySelector('#status').textContent = 'Status indisponível'; });
