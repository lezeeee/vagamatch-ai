# Validation

Validation date: **13 November 2026**. Local Windows machine, Python 3.11, 32 GB RAM and an NVIDIA RTX 3050 Laptop GPU. Ollama 0.40.16 with `qwen3:4b-instruct-2507-q4_K_M`; RapidOCR with the checksum-verified Latin recognition model.

## Automated checks

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pip check
node --check app/static/app.js
```

- **56 tests passed.**
- No broken package requirements were reported.
- JavaScript syntax check passed.

The tests simulate the local model transport. They cover upload limits, digital/scanned/mixed PDFs, PNG/JPG inputs, OCR fallback, password-protected or unreadable documents, source-ID integrity, duplicate/conflicting results, negation, common named technologies, API error stages and the English interface. The tests do not measure model accuracy.

## Real inference and OCR

These requests used the real local language model and, where needed, real OCR. Timing includes document reading and inference; the model was already loaded. No paid service was used.

| Input | HTTP result | Observed time | Source checks |
| --- | --- | --- | --- |
| Included English sample PDF | 200 | 3.7 s | Passed |
| Previously downloaded Portuguese sample PDF | 200 | 3.4 s | Passed |
| Owner's private one-page resume PDF | 200 | 6.8 s | Passed |
| Image-only PDF made from the fictional sample | 200 | 9.1 s | Passed; OCR used |
| Image-only copy of the private resume | 200 | 26.1 s | Passed; OCR used |
| PNG copy of the private resume | 200 | 25.8 s | Passed; OCR used |

The fictional samples produced **Met** for Java/OOP, **Partially met** for SQL/PostgreSQL, and **Not found** for Python/FastAPI. Every displayed excerpt was checked against the text extracted from the corresponding page. No generated quotation had to be copied or repaired.

Private document contents, names, contact details, screenshots and analysis outputs were **not** committed. Only these aggregate observations are recorded here.

## Browser check

The English interface was exercised with the fictional sample: file upload, analysis, category filtering, expanding evidence and a follow-up question. The answer correctly stated that the sample contains no Python experience and suggested a future learning project. The screenshot in `docs/screenshot.png` contains only fictional data.

## What this does not establish

Successful HTTP responses and literal excerpts do not prove that every classification is correct. OCR can miss or change words and can therefore change a result. The scanned private resume did not receive the same classifications as its digital original. Users must review the excerpts; use the digital original when available.

These timings are measurements on one machine, not latency guarantees. Cold model startup, longer jobs, larger scans and concurrent computer activity can increase response time. The application remains a basic local portfolio demo, with no database or saved history; it has not been deployed as an internet service.
