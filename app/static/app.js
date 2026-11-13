const form = document.querySelector('#analysis-form');
const fileInput = document.querySelector('#resume');
const jobInput = document.querySelector('#job');
const message = document.querySelector('#message');
const results = document.querySelector('#results');
const submit = document.querySelector('#submit');
const statusFilter = document.querySelector('#status-filter');
const questionForm = document.querySelector('#question-form');
const answerBox = document.querySelector('#answer');
const askMessage = document.querySelector('#ask-message');
let activeMode = 'ollama';
let apiReady = false;
const labels = {atendido: 'Atendido', parcialmente_atendido: 'Parcialmente atendido', nao_encontrado: 'Não encontrado'};

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text; // PDF and job text are always rendered as text, never HTML.
  if (className) node.className = className;
  return node;
}
function clearResults() {
  results.hidden = true;
  document.querySelector('#result-list').replaceChildren();
  document.querySelector('#summary').replaceChildren();
  document.querySelector('#result-notice').textContent = '';
  document.querySelector('#empty-filter').hidden = true;
  statusFilter.value = 'all';
  questionForm.hidden = true;
  questionForm.reset();
  answerBox.replaceChildren();
  askMessage.textContent = '';
}

function filterResults() {
  let visible = 0;
  for (const card of document.querySelectorAll('.result-card')) {
    card.hidden = statusFilter.value !== 'all' && card.dataset.status !== statusFilter.value;
    if (!card.hidden) visible++;
  }
  document.querySelector('#empty-filter').hidden = visible > 0;
}
function showAnalysis(data) {
  document.querySelector('#result-notice').textContent = data.notice;
  const list = document.querySelector('#result-list');
  const counts = [];
  for (const [status, label] of Object.entries(labels)) {
    const count = data.results.filter(item => item.status === status).length;
    counts.push(`${label}: ${count}`);
  }
  document.querySelector('#summary').textContent = counts.join(' | ');
  for (const item of data.results) {
    const card = element('details', undefined, 'result-card');
    card.dataset.status = item.status;
    const top = element('summary');
    top.append(element('strong', item.requirement), element('span', labels[item.status], `badge ${item.status}`));
    const body = element('div', undefined, 'result-body');
    body.append(element('p', item.explanation));
    for (const proof of item.evidence) {
      const quote = element('blockquote', proof.quote);
      quote.append(element('cite', `Currículo · página ${proof.page}`));
      body.append(quote);
    }
    if (item.evidence.length === 0) body.append(element('p', 'Nenhum trecho do currículo encontrado.'));
    body.append(element('p', `Sugestão: ${item.suggestion}`));
    card.append(top, body);
    list.append(card);
  }
  results.hidden = false;
  questionForm.hidden = !['openai', 'ollama'].includes(data.mode);
  document.querySelector('#results-title').focus();
}
fileInput.addEventListener('change', () => {
  clearResults();
  message.textContent = '';
});
jobInput.addEventListener('input', clearResults);
statusFilter.addEventListener('change', filterResults);
document.querySelector('#example').addEventListener('click', () => {
  jobInput.value = 'Conhecimento em Java e POO\nSQL e PostgreSQL\nPython e FastAPI';
  clearResults();
});
document.querySelector('#clear').addEventListener('click', () => {
  form.reset();
  fileInput.dispatchEvent(new Event('change'));
  jobInput.focus();
});
form.addEventListener('submit', async event => {
  event.preventDefault();
  clearResults();
  message.textContent = '';
  const file = fileInput.files[0];
  if (!file || file.size > 5 * 1024 * 1024) {
    message.textContent = 'Selecione um PDF de até 5 MB.';
    return;
  }
  const payload = new FormData(form);
  // Freeze the inputs so a result always belongs to the displayed submission.
  const controls = [...form.querySelectorAll('input, textarea, button')];
  controls.forEach(control => control.disabled = true);
  submit.textContent = activeMode === 'demo' ? 'Comparando…' : 'Analisando com IA…';
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), activeMode === 'ollama' ? 190000 : 60000);
  try {
    const response = await fetch('/api/analyze', {method: 'POST', body: payload, signal: controller.signal, cache: 'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Não foi possível analisar. Confira o formulário.');
    showAnalysis(data);
  } catch (error) {
    message.textContent = error.name === 'AbortError' ? 'A análise demorou demais. Tente um PDF menor.' : (error instanceof TypeError ? 'Não foi possível conectar ao servidor. Verifique se ele está em execução.' : error.message);
  } finally {
    clearTimeout(timeout);
    controls.forEach(control => control.disabled = false);
    submit.textContent = activeMode === 'demo' ? 'Comparar sem IA' : 'Analisar com IA';
    submit.disabled = !apiReady;
  }
});

questionForm.addEventListener('submit', async event => {
  event.preventDefault();
  const payload = new FormData(form);
  payload.append('question', document.querySelector('#question').value);
  const controls = [...document.querySelectorAll('form input, form textarea, form button')];
  controls.forEach(control => control.disabled = true);
  const askSubmit = document.querySelector('#ask-submit');
  askSubmit.textContent = 'Respondendo…';
  askMessage.textContent = '';
  answerBox.replaceChildren();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), activeMode === 'ollama' ? 190000 : 60000);
  try {
    const response = await fetch('/api/ask', {method: 'POST', body: payload, signal: controller.signal, cache: 'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Não foi possível responder. Tente novamente.');
    answerBox.append(element('p', data.answer));
    for (const proof of data.evidence) {
      const quote = element('blockquote', proof.quote);
      quote.append(element('cite', `Currículo · página ${proof.page}`));
      answerBox.append(quote);
    }
  } catch (error) {
    askMessage.textContent = error.name === 'AbortError' ? 'A resposta demorou demais. Tente novamente.' : (error instanceof TypeError ? 'Não foi possível conectar ao servidor.' : error.message);
  } finally {
    clearTimeout(timeout);
    controls.forEach(control => control.disabled = false);
    askSubmit.textContent = 'Perguntar';
    submit.disabled = !apiReady;
  }
});

async function loadConfiguration() {
  const notice = document.querySelector('#config-message');
  try {
    const response = await fetch('/api/health', {cache: 'no-store'});
    if (!response.ok) throw new Error('Configuração indisponível.');
    const config = await response.json();
    activeMode = config.mode;
    apiReady = config.ready === true;
    notice.textContent = config.message;
    document.querySelector('#privacy-message').textContent = activeMode === 'ollama'
      ? 'Projeto de Eliese. A IA roda neste computador, sem enviar o currículo a serviços externos. Sem histórico de currículos e sem nota de contratação.'
      : activeMode === 'demo' ? 'Projeto de Eliese. Modo demonstração sem IA, sem histórico de currículos e sem nota de contratação.'
      : 'Projeto de Eliese. No modo OpenAI, o texto do currículo e a vaga são enviados à OpenAI. Sem histórico de currículos e sem nota de contratação.';
    submit.textContent = activeMode === 'demo' ? 'Comparar sem IA' : 'Analisar com IA';
    submit.disabled = !apiReady;
  } catch {
    notice.textContent = 'Servidor indisponível. Inicie a aplicação e atualize a página.';
    submit.disabled = true;
  }
}
loadConfiguration();
