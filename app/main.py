from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app.analyzer import analyze
from app.ai_service import AIServiceError, analyze_with_ai, answer_with_ai, local_status, require_ready
from app.config import LOCAL_MODEL, MODEL, Settings, get_settings
from app.models import Analysis, Answer
from app.pdf_reader import InvalidPDF, extract_pages
from app.uploads import read_submission

STATIC = Path(__file__).parent / 'static'
app = FastAPI(title='VagaMatch AI', version='0.3.0', description='Comparação de currículo e vaga com IA local gratuita.')
app.mount('/static', StaticFiles(directory=STATIC), name='static')


@app.middleware('http')
async def privacy_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'" if request.url.path != '/docs' else "default-src 'self' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net"
    return response


@app.get('/', include_in_schema=False)
def home():
    return FileResponse(STATIC / 'index.html')


@app.get('/api/health')
async def health(settings: Settings = Depends(get_settings)):
    ready = settings.ready
    if settings.mode == 'demo':
        message = 'Modo demonstração: palavras-chave, sem IA.'
    elif settings.mode == 'ollama':
        ready, message = await local_status()
    elif not settings.ready:
        message = 'IA aguardando configuração no servidor. Execute configurar_api.py no terminal.'
    else:
        message = 'API de IA configurada no servidor. A conexão será verificada ao analisar.'
    return {'status': 'ok', 'mode': settings.mode, 'ready': ready, 'message': message,
            'model': LOCAL_MODEL if settings.mode == 'ollama' else MODEL if settings.mode == 'openai' else None,
            'external_api_enabled': settings.mode == 'openai' and settings.ready}


@app.post('/api/analyze', response_model=Analysis)
async def analyze_resume(request: Request, settings: Settings = Depends(get_settings)):
    try:
        if settings.mode != 'demo':
            require_ready(settings)
        content, job, _ = await read_submission(request)
        pages = await run_in_threadpool(extract_pages, content)
        if settings.mode == 'demo':
            return await run_in_threadpool(analyze, pages, job)
        return await analyze_with_ai(pages, job, settings)
    except AIServiceError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    except InvalidPDF as exc:
        raise HTTPException(422, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post('/api/ask', response_model=Answer)
async def ask_about_resume(request: Request, settings: Settings = Depends(get_settings)):
    try:
        require_ready(settings)
        content, job, question = await read_submission(request, allow_question=True)
        pages = await run_in_threadpool(extract_pages, content)
        return await answer_with_ai(pages, job, question, settings)
    except AIServiceError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    except (InvalidPDF, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
