"""One-time, checksum-verified Latin recognition model download. No document data is sent."""
import hashlib
import urllib.request
from pathlib import Path

OCR_MODEL_PATH = Path(__file__).resolve().parents[1] / '.runtime/ocr/latin-rec.onnx'
OCR_MODEL_URL = 'https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.10.0/onnx/PP-OCRv4/rec/latin_PP-OCRv3_rec_mobile.onnx'
OCR_MODEL_SHA256 = 'e9d7a33667e8aaa702862975186adf2012e3f390cc0f9422865957125f8071cf'


def valid_ocr_model() -> bool:
    if not OCR_MODEL_PATH.is_file():
        return False
    with OCR_MODEL_PATH.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest() == OCR_MODEL_SHA256


def ensure_ocr_model():
    if valid_ocr_model():
        return
    OCR_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    partial = OCR_MODEL_PATH.with_suffix('.part')
    with urllib.request.urlopen(OCR_MODEL_URL, timeout=60) as response, partial.open('wb') as output:
        while chunk := response.read(256 * 1024):
            output.write(chunk)
    with partial.open('rb') as source:
        if hashlib.file_digest(source, 'sha256').hexdigest() != OCR_MODEL_SHA256:
            partial.unlink()
            raise RuntimeError('The OCR model failed its integrity check. Run the launcher again.')
    partial.replace(OCR_MODEL_PATH)
