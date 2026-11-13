from io import BytesIO

from pypdf import PdfReader

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_PAGES = 10
MAX_TEXT_CHARS = 40_000


class InvalidPDF(ValueError):
    pass


def extract_pages(content: bytes) -> list[str]:
    """Read only in memory. OCR and password-protected PDFs are not supported."""
    if not content or len(content) > MAX_FILE_BYTES:
        raise InvalidPDF('Envie um PDF de até 5 MB.')
    if not content.startswith(b'%PDF-'):
        raise InvalidPDF('O arquivo enviado não é um PDF válido.')
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            raise InvalidPDF('Envie um PDF sem senha.')
        if not 1 <= len(reader.pages) <= MAX_PAGES:
            raise InvalidPDF('O currículo deve ter entre 1 e 10 páginas.')
        pages = []
        total = 0
        for page in reader.pages:
            text = page.extract_text() or ''
            total += len(text)
            if total > MAX_TEXT_CHARS:
                raise InvalidPDF('O PDF excede o limite de 40 mil caracteres extraídos.')
            pages.append(text)
    except InvalidPDF:
        raise
    except Exception as exc:
        raise InvalidPDF('Não foi possível ler o PDF. Exporte o currículo novamente.') from exc
    if not any(text.strip() for text in pages):
        raise InvalidPDF('Não encontrei texto no PDF. PDFs escaneados precisam de OCR; use um PDF com texto selecionável.')
    return pages
