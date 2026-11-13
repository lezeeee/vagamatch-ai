"""Read digital PDFs, scanned PDFs and images entirely in memory."""
import math
import threading
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader
from app.ocr_model import OCR_MODEL_PATH, valid_ocr_model

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_PAGES = 10
MAX_TEXT_CHARS = 40_000
MAX_PIXELS = 12_000_000
_ocr_lock = threading.Lock()
_pdfium_lock = threading.Lock()


class InvalidPDF(ValueError):
    """A document reading error, also used for supported image inputs."""


class OCRUnavailable(RuntimeError):
    """An OCR setup failure must not be reported as an invalid document."""


@dataclass
class ResumeDocument:
    pages: list[str]
    ocr_pages: list[int]


@lru_cache(maxsize=1)
def ocr_engine():
    from rapidocr_onnxruntime import RapidOCR
    if not valid_ocr_model():
        raise OCRUnavailable('The local OCR model is missing or incomplete. Run iniciar.py to prepare it.')
    try:
        return RapidOCR(rec_model_path=str(OCR_MODEL_PATH), intra_op_num_threads=4, inter_op_num_threads=1)
    except Exception as error:
        raise OCRUnavailable('The local OCR engine could not start. Run the launcher again.') from error


def recognize_image(image: Image.Image) -> str:
    import numpy as np
    with _ocr_lock:
        result, _ = ocr_engine()(np.asarray(image.convert('RGB')))
    return '\n'.join(row[1] for row in (result or []) if row[2] >= .45)


def rendered_page(content: bytes, index: int) -> Image.Image:
    import pypdfium2 as pdfium
    # PDFium must not be called concurrently, even for separate documents.
    with _pdfium_lock:
        with pdfium.PdfDocument(content) as document:
            page = document[index]
            width, height = page.get_size()
            if width <= 0 or height <= 0:
                raise InvalidPDF('This PDF contains an invalid page size.')
            scale = min(2.5, math.sqrt(MAX_PIXELS / (width * height)))
            bitmap = page.render(scale=scale)
            try:
                return bitmap.to_pil().convert('RGB').copy()
            finally:
                bitmap.close()
                page.close()


def has_readable_text(text: str) -> bool:
    return sum(char.isalpha() for char in text) >= 25 and text.count('\ufffd') < max(3, len(text) // 30)


def read_resume(content: bytes) -> ResumeDocument:
    if not content or len(content) > MAX_FILE_BYTES:
        raise InvalidPDF('Upload a PDF, PNG or JPG file up to 5 MB.')
    pages = []
    ocr_pages = []
    try:
        if content.startswith(b'%PDF-'):
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted:
                raise InvalidPDF('This PDF is password-protected. Upload a copy without a password.')
            if not 1 <= len(reader.pages) <= MAX_PAGES:
                raise InvalidPDF('The resume must contain between 1 and 10 pages.')
            for index, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ''
                except Exception:
                    text = ''
                if not has_readable_text(text):
                    with rendered_page(content, index) as image:
                        recognized = recognize_image(image)
                    if recognized.strip():
                        text = recognized
                        ocr_pages.append(index + 1)
                pages.append(text)
                if sum(map(len, pages)) > MAX_TEXT_CHARS:
                    raise InvalidPDF('The extracted resume exceeds 40,000 characters. Upload a shorter resume.')
        elif content.startswith((b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff')):
            with Image.open(BytesIO(content)) as source:
                if source.width * source.height > 24_000_000:
                    raise InvalidPDF('This image is too large. Use a scan or photo below 24 megapixels.')
                image = ImageOps.exif_transpose(source).convert('RGB')
                try:
                    image.thumbnail((3000, 4000))
                    pages.append(recognize_image(image))
                    ocr_pages.append(1)
                finally:
                    image.close()
        else:
            raise InvalidPDF('Unsupported or invalid file. Upload a PDF, PNG or JPG resume.')
    except (InvalidPDF, OCRUnavailable):
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError) as error:
        raise InvalidPDF('The image could not be safely read. Upload a smaller PNG or JPG.') from error
    except Exception as error:
        raise InvalidPDF('This document could not be read. Try exporting the PDF again or uploading a clear image.') from error
    if not any(has_readable_text(text) for text in pages):
        raise InvalidPDF('No readable text was found, even with OCR. Upload a clearer scan or a PDF with selectable text.')
    if sum(map(len, pages)) > MAX_TEXT_CHARS:
        raise InvalidPDF('The extracted resume exceeds 40,000 characters. Upload a shorter resume.')
    return ResumeDocument(pages, ocr_pages)


def extract_pages(content: bytes) -> list[str]:
    return read_resume(content).pages
