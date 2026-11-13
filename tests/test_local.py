"""Ollama integration with simulated HTTP; live local checks are recorded separately."""
import json

import httpx2
import pytest
from fastapi.testclient import TestClient

from app import ai_service
from app.config import LOCAL_API, LOCAL_MODEL
from app.main import app
from examples.create_sample import make_pdf

QUOTE = 'Projeto academico em Java e programacao orientada a objetos.'


@pytest.fixture(autouse=True)
def local_configuration(monkeypatch):
    monkeypatch.setenv('VAGAMATCH_MODE', 'ollama')
    monkeypatch.setenv('OPENAI_API_KEY', '')
    monkeypatch.setenv('VAGAMATCH_ALLOW_PAID_API', 'false')

    def no_paid_calls(**kwargs):
        raise AssertionError('Local mode must never create an OpenAI client')
    monkeypatch.setattr(ai_service, 'AsyncOpenAI', no_paid_calls)


def mock_local(monkeypatch, payload=None, status_code=200, done=True, done_reason='stop', fail=None, model_installed=True):
    calls = []
    original_client = httpx2.AsyncClient

    async def transport(request):
        assert str(request.url).startswith(LOCAL_API + '/api/')
        assert 'authorization' not in request.headers
        if fail:
            raise fail('local test error', request=request)
        if request.url.path == '/api/tags':
            return httpx2.Response(200, json={'models': [{'name': LOCAL_MODEL}] if model_installed else []})
        calls.append(json.loads(request.content))
        selected = payload[min(len(calls) - 1, len(payload) - 1)] if isinstance(payload, list) else payload
        report = selected if selected is not None else {'results': [{
            'requirement': 'Java e POO', 'status': 'atendido',
            'evidence': [{'page': 1, 'quote': QUOTE}], 'explanation': 'O currículo cita um projeto acadêmico.'}]}
        return httpx2.Response(status_code, json={'done': done, 'done_reason': done_reason,
                                                 'message': {'role': 'assistant', 'content': json.dumps(report)}})

    monkeypatch.setattr(ai_service.httpx2, 'AsyncClient', lambda **kwargs: original_client(
        **kwargs, transport=httpx2.MockTransport(transport)))
    return calls


def submit(question=None):
    data = {'job_description': 'Java e POO'}
    if question is not None:
        data['question'] = question
    with TestClient(app) as client:
        return client.post('/api/ask' if question is not None else '/api/analyze',
                           files={'resume': ('example.pdf', make_pdf(), 'application/pdf')}, data=data)


def test_analysis_with_local_api_and_no_paid_fallback(monkeypatch):
    calls = mock_local(monkeypatch)
    response = submit()
    assert response.status_code == 200, response.text
    assert response.json()['mode'] == 'ollama'
    assert response.json()['results'][0]['evidence'][0]['quote'] == QUOTE
    assert len(calls) == 1
    assert calls[0]['model'] == LOCAL_MODEL
    assert calls[0]['think'] is False
    assert calls[0]['stream'] is False
    assert calls[0]['truncate'] is False
    assert calls[0]['format']['type'] == 'object'


def test_question_with_local_model(monkeypatch):
    calls = mock_local(monkeypatch, {'answer': 'Detalhe sua contribuição real no projeto em Java.',
                                    'evidence': [{'page': 1, 'quote': QUOTE}]})
    response = submit('O que posso explicar melhor?')
    assert response.status_code == 200
    assert response.json()['mode'] == 'ollama'
    assert json.loads(calls[0]['messages'][1]['content'])['question'] == 'O que posso explicar melhor?'


@pytest.mark.parametrize('status_code, expected', [(404, 503), (429, 429), (500, 502)])
def test_local_errors_no_fallback(monkeypatch, status_code, expected):
    calls = mock_local(monkeypatch, status_code=status_code)
    assert submit().status_code == expected
    assert len(calls) == 1


@pytest.mark.parametrize('error, expected', [(httpx2.ConnectError, 503), (httpx2.ReadTimeout, 504)])
def test_local_offline_and_timeout(monkeypatch, error, expected):
    mock_local(monkeypatch, fail=error)
    assert submit().status_code == expected


def test_invalid_local_json_rejected(monkeypatch):
    mock_local(monkeypatch, {'results': []})
    assert submit().status_code == 502


def test_local_invented_evidence_is_rejected(monkeypatch):
    mock_local(monkeypatch, {'results': [{'requirement': 'Java e POO', 'status': 'atendido',
                                       'evidence': [{'page': 1, 'quote': 'Tenho 10 anos de experiência em Java.'}],
                                       'explanation': 'A pessoa tem experiência profissional.'}]})
    assert submit().status_code == 502


def test_truncated_local_output_is_rejected(monkeypatch):
    mock_local(monkeypatch, done_reason='length')
    assert submit().status_code == 502


@pytest.mark.parametrize('installed', [True, False])
def test_health_checks_actual_model_presence(monkeypatch, installed):
    mock_local(monkeypatch, model_installed=installed)
    with TestClient(app) as client:
        data = client.get('/api/health').json()
    assert data['ready'] is installed
    assert data['mode'] == 'ollama'
    assert data['external_api_enabled'] is False


def test_health_reports_ollama_offline(monkeypatch):
    mock_local(monkeypatch, fail=httpx2.ConnectError)
    with TestClient(app) as client:
        data = client.get('/api/health').json()
    assert data['ready'] is False
    assert 'desligada' in data['message']


def test_inconsistent_local_evidence_is_repaired_once(monkeypatch):
    valid = {'results': [{'requirement': 'Java e POO', 'status': 'atendido',
                          'evidence': [{'page': 1, 'quote': QUOTE}], 'explanation': 'Projeto acadêmico em Java e POO.'}]}
    invalid = {'results': [{**valid['results'][0], 'evidence': []}]}
    calls = mock_local(monkeypatch, [invalid, valid])
    response = submit()
    assert response.status_code == 200
    assert len(calls) == 2
    repair = json.loads(calls[1]['messages'][1]['content'])['repair']
    assert repair['previous_response'] == invalid
    assert 'validation_error' in repair


def test_local_repair_does_not_loop_or_silently_use_demo(monkeypatch):
    calls = mock_local(monkeypatch, {'results': [{'requirement': 'Java e POO', 'status': 'atendido',
                                                'evidence': [], 'explanation': 'Sem citação.'}]})
    response = submit()
    assert response.status_code == 502
    assert len(calls) == 2
    assert 'results' not in response.json()


def test_denial_cannot_be_used_as_qualification_proof():
    from app.models import AIReport
    denial = 'Nao tenho experiencia em Python.'
    report = AIReport.model_validate({'results': [{'requirement': 'Python', 'status': 'atendido',
                                                 'evidence': [{'page': 1, 'quote': denial}],
                                                 'explanation': 'Experiência em Python.'}]})
    with pytest.raises(ai_service.AIServiceError, match='negação'):
        ai_service.validated_analysis(report, [denial], 'Python', 'ollama')


def test_duplicate_evidence_is_merged_before_validation():
    from app.models import AIReport
    base = {'requirement': 'Java e POO', 'status': 'atendido', 'explanation': 'Projeto acadêmico.'}
    report = AIReport.model_validate({'results': [{**base, 'evidence': []},
                                                {**base, 'evidence': [{'page': 1, 'quote': QUOTE}]}]})
    result = ai_service.validated_analysis(report, [QUOTE], 'Java e POO', 'ollama')
    assert len(result.results) == 1
    assert result.results[0].evidence[0].quote == QUOTE
