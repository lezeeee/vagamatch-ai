"""Generate a tiny fictional text PDF using pypdf, also used by the tests."""
from io import BytesIO
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def make_pdf(lines: list[str] | None = None) -> bytes:
    lines = lines if lines is not None else [
        'FICTIONAL RESUME - DEMONSTRATION ONLY',
        'Software Engineering student.',
        'Academic project using Java and object-oriented programming.',
        'SQL query exercises for a database course.',
        'Web interface using HTML, CSS and JavaScript.',
    ]
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    commands = ['BT /F1 12 Tf 45 780 Td 22 TL']
    for line in lines:
        escaped = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        commands.append(f'({escaped}) Tj T*')
    commands.append('ET')
    stream.set_data('\n'.join(commands).encode('latin-1'))
    page[NameObject('/Contents')] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    (root / 'app/static/curriculo-exemplo.pdf').write_bytes(make_pdf())
