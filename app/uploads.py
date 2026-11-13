"""Bounded multipart parsing without UploadFile's temporary-disk spooling."""
from fastapi import HTTPException, Request
from python_multipart import create_form_parser

from app.pdf_reader import MAX_FILE_BYTES

MAX_BODY_BYTES = MAX_FILE_BYTES + 64 * 1024


async def read_submission(request: Request, allow_question: bool = False) -> tuple[bytes, str, str | None]:
    content_type = request.headers.get('content-type', '')
    if not content_type.lower().startswith('multipart/form-data;'):
        raise HTTPException(415, 'Send a resume file and job description as a multipart form.')
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY_BYTES:
            raise HTTPException(413, 'The upload is too large. Use a file up to 5 MB.')
        body.extend(chunk)
    fields = {}
    files = {}

    def on_field(field):
        allowed = {b'job_description', b'question'} if allow_question else {b'job_description'}
        if field.field_name not in allowed or field.field_name in fields:
            raise ValueError('Invalid or duplicate field.')
        fields[field.field_name] = (field.value or b'').decode('utf-8')

    def on_file(file):
        try:
            if file.field_name != b'resume' or file.field_name in files:
                raise ValueError('Invalid or duplicate file.')
            if not file.in_memory:
                raise ValueError('Uploads must stay in memory.')
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
        raise HTTPException(422, 'Invalid form. Select a PDF, PNG or JPG and enter the job description.') from exc
    expected_fields = {b'job_description', b'question'} if allow_question else {b'job_description'}
    if set(files) != {b'resume'} or set(fields) != expected_fields:
        raise HTTPException(422, 'Select a resume file and enter the job description.')
    job = fields[b'job_description'].strip()
    if not 3 <= len(job) <= 12_000:
        raise HTTPException(422, 'The job description must contain between 3 and 12,000 characters.')
    question = fields.get(b'question', '').strip() if allow_question else None
    if allow_question and not 3 <= len(question) <= 1000:
        raise HTTPException(422, 'The question must contain between 3 and 1,000 characters.')
    return files[b'resume'], job, question
