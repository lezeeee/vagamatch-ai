"""One-command Windows launcher for the free, local version. Standard library only."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import venv
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / '.runtime'
MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
OLLAMA_URL = 'http://127.0.0.1:11434'
OLLAMA_VERSION = '0.40.16'
ARCHIVE_HASH = '50fcf5ad54277f2fa5d173ebfc93bcb017adbc0c9ef2314daabc96ca9e6aa64e'


def local_json(path: str, payload=None, timeout=3):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(OLLAMA_URL + path, data=data, headers={'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        return json.load(response)


def find_runtime() -> Path:
    candidates = [RUNTIME / 'ollama/ollama.exe', ROOT.parent.parent / 'work/ollama-runtime/ollama.exe']
    installed = shutil.which('ollama')
    if installed:
        candidates.append(Path(installed))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    if os.name != 'nt':
        raise RuntimeError('Install Ollama from https://ollama.com/download, then run this launcher again.')
    print('Downloading the official Ollama runtime (about 1.6 GB). This is a one-time download.', flush=True)
    archive = RUNTIME / 'ollama-windows-amd64.zip'
    url = f'https://github.com/ollama/ollama/releases/download/v{OLLAMA_VERSION}/ollama-windows-amd64.zip'
    urllib.request.urlretrieve(url, archive)
    with archive.open('rb') as downloaded:
        checksum = hashlib.file_digest(downloaded, 'sha256').hexdigest()
    if checksum != ARCHIVE_HASH:
        archive.unlink()
        raise RuntimeError('The runtime download failed its integrity check. Please try again.')
    target = RUNTIME / 'ollama'
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            if not (target / entry.filename).resolve().is_relative_to(target.resolve()):
                raise RuntimeError('An invalid path was found in the Ollama archive.')
        bundle.extractall(target)
    archive.unlink()
    return target / 'ollama.exe'


def ensure_model_server():
    try:
        local_json('/api/version')
        return
    except (OSError, ValueError):
        pass
    binary = find_runtime()
    existing_models = ROOT.parent.parent / 'work/ollama-models'
    models = existing_models if existing_models.is_dir() else RUNTIME / 'models'
    models.mkdir(parents=True, exist_ok=True)
    environment = {**os.environ,
                   'OLLAMA_HOST': '127.0.0.1:11434', 'OLLAMA_MODELS': str(models),
                   'OLLAMA_NO_CLOUD': '1', 'OLLAMA_NOHISTORY': '1',
                   'OLLAMA_DEBUG_LOG_REQUESTS': 'false', 'OLLAMA_NUM_PARALLEL': '1',
                   'OLLAMA_FLASH_ATTENTION': '1', 'OLLAMA_KV_CACHE_TYPE': 'q8_0'}
    with (RUNTIME / 'ollama.log').open('ab') as log:
        subprocess.Popen([str(binary), 'serve'], cwd=ROOT, env=environment,
                         stdout=log, stderr=log,
                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    for _ in range(60):
        try:
            local_json('/api/version')
            return
        except (OSError, ValueError):
            time.sleep(.5)
    raise RuntimeError('Ollama did not start. See .runtime/ollama.log.')


def ensure_model():
    names = {model['name'] for model in local_json('/api/tags').get('models', [])}
    if MODEL not in names:
        print('Downloading the local AI model (about 2.5 GB). This is a one-time download.', flush=True)
        result = local_json('/api/pull', {'model': MODEL, 'stream': False}, timeout=1800)
        if result.get('status') != 'success':
            raise RuntimeError('The model download did not finish. Run this launcher again to continue.')


def app_is_running():
    from app.config import APP_VERSION
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open('http://127.0.0.1:8000/openapi.json', timeout=2) as response:
            info = json.load(response).get('info', {})
    except (OSError, ValueError):
        return False
    if info.get('title') == 'VagaMatch AI' and info.get('version') == APP_VERSION:
        return True
    raise RuntimeError('Another app or an older VagaMatch version is using port 8000. Close it and run this launcher again.')


def main():
    os.chdir(ROOT)
    RUNTIME.mkdir(exist_ok=True)
    python = ROOT / ('.venv/Scripts/python.exe' if os.name == 'nt' else '.venv/bin/python')
    if not python.exists():
        print('Creating the Python environment...', flush=True)
        venv.create(ROOT / '.venv', with_pip=True)
    check = subprocess.run([str(python), '-c', 'import fastapi, uvicorn, pypdf, python_multipart, httpx2, PIL, pypdfium2, rapidocr_onnxruntime'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if check.returncode:
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')], check=True)
    print('Preparing the local English/Portuguese OCR model...', flush=True)
    subprocess.run([str(python), '-c', 'from app.ocr_model import ensure_ocr_model; ensure_ocr_model()'], check=True)
    ensure_model_server()
    ensure_model()
    if app_is_running():
        print('VagaMatch AI is already running. Open http://127.0.0.1:8000 or refresh the page.', flush=True)
        return 0
    print('Loading local AI before starting the app...', flush=True)
    local_json('/api/generate', {'model': MODEL, 'stream': False, 'keep_alive': '20m',
                                'options': {'num_ctx': 8192}}, timeout=120)
    environment = dict(os.environ)
    print('Ready. Open http://127.0.0.1:8000 — Ctrl+C stops the app.', flush=True)
    try:
        return subprocess.call([str(python), '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
                                '--port', '8000', '--no-access-log'], env=environment)
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'Could not start VagaMatch AI: {error}', file=sys.stderr)
        raise SystemExit(1)
