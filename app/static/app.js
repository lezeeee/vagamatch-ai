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
const processing = document.querySelector('#processing');
const labels = {met: 'Met', partial: 'Partially met', not_found: 'Not found'};
let apiReady = false;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function clearResults() {
  results.hidden = true;
  document.querySelector('#result-list').replaceChildren();
  document.querySelector('#summary').textContent = '';
  document.querySelector('#warnings').textContent = '';
  document.querySelector('#warnings').hidden = true;
  document.querySelector('#empty-filter').hidden = true;
  statusFilter.value = 'all';
  questionForm.reset();
  questionForm.hidden = true;
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
function addEvidence(target, evidence) {
  for (const proof of evidence) {
    const quote = element('blockquote', proof.quote);
    quote.append(element('cite', `Resume · page ${proof.page}`));
    target.append(quote);
  }
}
function showAnalysis(data) {
  document.querySelector('#result-notice').textContent = data.notice;
  const reading = data.reading;
  document.querySelector('#reading-info').textContent = `Read ${reading.pages} page(s). Completed in ${data.elapsed_seconds}s.` +
    (reading.ocr_pages.length ? ` OCR used on page(s) ${reading.ocr_pages.join(', ')}. Check the excerpts for recognition errors.` : '');
  const warnings = document.querySelector('#warnings');
  warnings.textContent = (data.warnings || []).join(' ');
  warnings.hidden = !warnings.textContent;
  document.querySelector('#summary').textContent = Object.entries(labels).map(([status, label]) =>
    `${label}: ${data.results.filter(item => item.status === status).length}`).join(' | ');
  const list = document.querySelector('#result-list');
  for (const item of data.results) {
    const card = element('details', undefined, 'result-card');
    card.dataset.status = item.status;
    const top = element('summary');
    top.append(element('strong', item.requirement), element('span', labels[item.status], `badge ${item.status}`));
    const body = element('div', undefined, 'result-body');
    body.append(element('p', item.explanation));
    addEvidence(body, item.evidence);
    if (!item.evidence.length) body.append(element('p', 'No verified positive excerpt was selected.'));
    body.append(element('p', `Suggestion: ${item.suggestion}`));
    card.append(top, body);
    list.append(card);
  }
  results.hidden = false;
  questionForm.hidden = false;
  document.querySelector('#results-title').focus();
}
function setBusy(busy) {
  document.querySelectorAll('form input, form textarea, form button').forEach(control => control.disabled = busy);
  if (!busy) submit.disabled = !apiReady;
}
function errorMessage(data) {
  const prefix = {document: 'Document', ai: 'AI service', job: 'Job description', ocr: 'OCR setup'}[data.stage];
  const detail = typeof data.detail === 'string' ? data.detail : 'The request could not be completed.';
  return prefix ? `${prefix}: ${detail}` : detail;
}
async function send(path, payload, label) {
  const started = Date.now();
  processing.hidden = false;
  const update = () => processing.textContent = `${label}… ${Math.floor((Date.now() - started) / 1000)}s. Scanned files may take a few extra seconds.`;
  update();
  const interval = setInterval(update, 1000);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 90000);
  try {
    const response = await fetch(path, {method: 'POST', body: payload, signal: controller.signal, cache: 'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(errorMessage(data));
    return data;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The request timed out. Try a shorter job description.');
    if (error instanceof TypeError) throw new Error('Cannot reach the local app. Make sure it is running.');
    throw error;
  } finally {
    clearInterval(interval);
    clearTimeout(timeout);
    processing.hidden = true;
  }
}
fileInput.addEventListener('change', () => { clearResults(); message.textContent = ''; });
jobInput.addEventListener('input', clearResults);
statusFilter.addEventListener('change', filterResults);
document.querySelector('#example').addEventListener('click', () => {
  jobInput.value = 'Knowledge of Java and object-oriented programming\nSQL and PostgreSQL\nPython and FastAPI';
  clearResults();
});
document.querySelector('#clear').addEventListener('click', () => {
  form.reset(); clearResults(); message.textContent = ''; jobInput.focus();
});
form.addEventListener('submit', async event => {
  event.preventDefault();
  clearResults();
  message.textContent = '';
  const file = fileInput.files[0];
  if (!file || file.size > 5 * 1024 * 1024) { message.textContent = 'Select a PDF, PNG or JPG up to 5 MB.'; return; }
  const payload = new FormData(form);
  setBusy(true);
  submit.textContent = 'Analyzing…';
  try { showAnalysis(await send('/api/analyze', payload, 'Reading and analyzing the resume')); }
  catch (error) { message.textContent = error.message; }
  finally { setBusy(false); submit.textContent = 'Analyze resume'; }
});
questionForm.addEventListener('submit', async event => {
  event.preventDefault();
  const payload = new FormData(form);
  payload.append('question', document.querySelector('#question').value);
  setBusy(true);
  askMessage.textContent = '';
  answerBox.replaceChildren();
  const askSubmit = document.querySelector('#ask-submit');
  askSubmit.textContent = 'Answering…';
  try {
    const data = await send('/api/ask', payload, 'Answering your question');
    answerBox.append(element('p', data.answer));
    addEvidence(answerBox, data.evidence);
  } catch (error) { askMessage.textContent = error.message; }
  finally { setBusy(false); askSubmit.textContent = 'Ask AI'; }
});
async function loadConfiguration() {
  const notice = document.querySelector('#config-message');
  try {
    const response = await fetch('/api/health', {cache: 'no-store'});
    if (!response.ok) throw new Error('Unavailable');
    const config = await response.json();
    apiReady = config.ready === true;
    notice.textContent = config.message;
    submit.disabled = !apiReady;
  } catch { notice.textContent = 'The local app is unavailable. Start it and refresh this page.'; submit.disabled = true; }
}
loadConfiguration();
