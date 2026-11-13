"""Bounded multipart parsing without UploadFile's temporary-disk spooling."""
from fastapi import HTTPException, Request
from python_multipart import create_form_parser

from app.pdf_reader import MAX_FILE_BYTES

MAX_BODY_BYTES = MAX_FILE_BYTES + 64 * 1024


async def read_submission(request: Request, allow_question: bool = False) -> tuple[bytes, str, str | None]:
    content_type = request.headers.get('content-type', '')
    if not content_type.lower().startswith('multipart/form-data;'):
        raise HTTPException(415, 'Envie o formulário com um PDF e a descrição da vaga.')
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY_BYTES:
            raise HTTPException(413, 'O envio excede o limite. Use um PDF de até 5 MB.')
        body.extend(chunk)
    fields = {}
    files = {}

    def on_field(field):
        allowed = {b'job_description', b'question'} if allow_question else {b'job_description'}
        if field.field_name not in allowed or field.field_name in fields:
            raise ValueError('Campo inválido ou duplicado.')
        fields[field.field_name] = (field.value or b'').decode('utf-8')

    def on_file(file):
        try:
            if file.field_name != b'resume' or file.field_name in files:
                raise ValueError('Arquivo inválido ou duplicado.')
            if not file.in_memory:
                raise ValueError('O arquivo deve ser processado em memória.')
            file.file_object.seek(0)
            files[file.field_name] = file.file_object.read()
        finally:
            file.close()

    try:
        parser = create_form_parser({'Content-Type': content_type.encode()}, on_field, on_file,
                                    config={'MAX_MEMORY_FILE_SIZE': MAX_BODY_BYTES, 'MAX_BODY_SIZE': MAX_BODY_BYTES})
        try:
            parser.write(bytes(body))
            parser.finalize()
        finally:
            parser.close()
    except Exception as exc:
        raise HTTPException(422, 'Formulário inválido. Selecione um PDF e preencha a vaga.') from exc
    expected_fields = {b'job_description', b'question'} if allow_question else {b'job_description'}
    if set(files) != {b'resume'} or set(fields) != expected_fields:
        raise HTTPException(422, 'Selecione um PDF e preencha a vaga.')
    job = fields[b'job_description'].strip()
    if not 3 <= len(job) <= 12_000:
        raise HTTPException(422, 'A descrição da vaga deve ter entre 3 e 12 mil caracteres.')
    question = fields.get(b'question', '').strip() if allow_question else None
    if allow_question and not 3 <= len(question) <= 1000:
        raise HTTPException(422, 'A pergunta deve ter entre 3 e 1000 caracteres.')
    return files[b'resume'], job, question
