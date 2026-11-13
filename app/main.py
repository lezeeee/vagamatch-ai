from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app.ai_service import AIServiceError, analyze_with_ai, answer_with_ai, local_status
from app.config import APP_VERSION, LOCAL_MODEL
from app.models import Analysis, Answer, ReadingSummary
from app.pdf_reader import InvalidPDF, OCRUnavailable, read_resume
from app.uploads import read_submission

STATIC = Path(__file__).parent / 'static'
app = FastAPI(title='VagaMatch AI', version=APP_VERSION,
              description='A basic AI resume matcher with OCR. No database or saved history.')
app.mount('/static', StaticFiles(directory=STATIC), name='static')


@app.middleware('http')
async def privacy_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    if request.url.path != '/docs':
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    return response


@app.exception_handler(InvalidPDF)
async def document_error(request, error):
    return JSONResponse(status_code=422, content={'detail': str(error), 'stage': 'document'})


@app.exception_handler(AIServiceError)
async def ai_error(request, error):
    return JSONResponse(status_code=error.status_code, content={'detail': str(error), 'stage': 'ai'})


@app.exception_handler(OCRUnavailable)
async def ocr_error(request, error):
    return JSONResponse(status_code=503, content={'detail': str(error), 'stage': 'ocr'})


@app.get('/', include_in_schema=False)
def home():
    return FileResponse(STATIC / 'index.html')


@app.get('/api/health')
async def health():
    ready, message = await local_status()
    return {'status': 'ok', 'mode': 'ollama', 'ready': ready, 'message': message,
            'model': LOCAL_MODEL, 'external_api_enabled': False}


@app.post('/api/analyze', response_model=Analysis)
async def analyze_resume(request: Request):
    started = perf_counter()
    content, job, _ = await read_submission(request)
    document = await run_in_threadpool(read_resume, content)
    try:
        result = await analyze_with_ai(document.pages, job)
    except ValueError as error:
        return JSONResponse(status_code=422, content={'detail': str(error), 'stage': 'job'})
    result.reading = ReadingSummary(pages=len(document.pages), ocr_pages=document.ocr_pages)
    result.elapsed_seconds = round(perf_counter() - started, 1)
    return result


@app.post('/api/ask', response_model=Answer)
async def ask_about_resume(request: Request):
    started = perf_counter()
    content, job, question = await read_submission(request, allow_question=True)
    document = await run_in_threadpool(read_resume, content)
    answer = await answer_with_ai(document.pages, job, question)
    answer.elapsed_seconds = round(perf_counter() - started, 1)
    return answer
