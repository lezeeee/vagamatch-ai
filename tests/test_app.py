from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.analyzer import analyze
from app.main import app
from app.pdf_reader import MAX_FILE_BYTES
from examples.create_sample import make_pdf

client = TestClient(app)


@pytest.fixture(autouse=True)
def demo_configuration(monkeypatch):
    monkeypatch.setenv('VAGAMATCH_MODE', 'demo')
    monkeypatch.setenv('OPENAI_API_KEY', '')
    monkeypatch.setenv('VAGAMATCH_ALLOW_PAID_API', 'false')


def submit(pdf=None, job='Java e POO\nSQL e PostgreSQL\nPython e FastAPI'):
    return client.post('/api/analyze', files={'resume': ('curriculo.pdf', make_pdf() if pdf is None else pdf, 'application/pdf')}, data={'job_description': job})


def test_full_flow_with_real_pdf_and_exact_evidence():
    response = submit()
    assert response.status_code == 200
    data = response.json()
    assert data['mode'] == 'demo'
    assert [item['status'] for item in data['results']] == ['atendido', 'parcialmente_atendido', 'nao_encontrado']
    assert data['results'][0]['evidence'] == [{'page': 1, 'quote': 'Projeto academico em Java e programacao orientada a objetos.'}]
    assert data['results'][2]['evidence'] == []
    assert response.headers['cache-control'] == 'no-store'
    assert 'score' not in data


def test_javascript_is_not_java_and_negation_is_not_proof():
    assert analyze(['JavaScript\nNao tenho experiencia em Java'], 'Java').results[0].status == 'nao_encontrado'


def test_experience_years_are_not_invented():
    result = analyze(['Projeto em Java'], '5 anos de experiencia em Java').results[0]
    assert result.status == 'parcialmente_atendido'


def test_evidence_keeps_page_and_original_text():
    result = analyze(['HTML', 'Consultas SQL'], 'SQL').results[0]
    assert result.evidence[0].page == 2
    assert result.evidence[0].quote == 'Consultas SQL'


@pytest.mark.parametrize('content', [b'', b'not a pdf', b'%PDF-1.7 corrupt'])
def test_invalid_pdf(content):
    assert submit(pdf=content).status_code == 422


def test_scanned_or_empty_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    out = BytesIO()
    writer.write(out)
    response = submit(pdf=out.getvalue())
    assert response.status_code == 422
    assert 'OCR' in response.json()['detail']


def test_encrypted_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt('test-password')
    out = BytesIO()
    writer.write(out)
    assert 'senha' in submit(pdf=out.getvalue()).json()['detail']


def test_page_limit():
    writer = PdfWriter()
    for _ in range(11):
        writer.add_blank_page(width=100, height=100)
    out = BytesIO()
    writer.write(out)
    assert submit(pdf=out.getvalue()).status_code == 422


@pytest.mark.parametrize('job', ['  ', 'a' * 12001, '\n'.join(f'Java {i}' for i in range(31))])
def test_job_limits(job):
    assert submit(job=job).status_code == 422


def test_size_limit_without_content_length():
    response = client.post('/api/analyze', content=iter([b'x' * (MAX_FILE_BYTES + 65537)]), headers={'Content-Type': 'multipart/form-data; boundary=abc'})
    assert response.status_code == 413


def test_large_upload_never_opens_temporary_file(monkeypatch):
    def forbid_disk(*args, **kwargs):
        raise AssertionError('An upload attempted to open a disk file')
    monkeypatch.setattr('tempfile.NamedTemporaryFile', forbid_disk)
    # Larger than python-multipart's default 1 MB spill threshold.
    assert submit(pdf=make_pdf() + b'\n' + b' ' * 1_100_000).status_code == 200


def test_oversized_pdf_within_body_limit():
    assert submit(pdf=b'%PDF-' + b' ' * MAX_FILE_BYTES).status_code == 422


def test_missing_fields_and_wrong_media_type():
    assert client.post('/api/analyze', json={}).status_code == 415
    assert client.post('/api/analyze', files={'resume': ('a.pdf', make_pdf())}).status_code == 422


def test_duplicate_files():
    response = client.post('/api/analyze', files=[('resume', ('a.pdf', make_pdf())), ('resume', ('b.pdf', make_pdf()))], data={'job_description': 'Java'})
    assert response.status_code == 422


def test_home_health_and_assets():
    assert client.get('/').status_code == 200
    assert client.get('/api/health').json()['external_api_enabled'] is False
    assert client.get('/static/app.js').status_code == 200
    assert client.get('/static/curriculo-exemplo.pdf').content.startswith(b'%PDF-')
