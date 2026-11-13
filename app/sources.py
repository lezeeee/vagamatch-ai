"""Assign references to original text; the model never needs to reproduce quotes."""
import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    id: str
    text: str
    page: int = 0


def split_text(text: str, maximum: int = 450) -> list[str]:
    parts = []
    # Newlines, bullets and sentence boundaries, preserving the original substrings.
    for line in re.split(r'\n+|;\s*|(?<=[.!?])\s+(?=[A-ZÀ-Ý])', text):
        line = line.strip(' \t\r•*-')
        while len(line) > maximum:
            cut = line.rfind(' ', 0, maximum)
            cut = cut if cut > 0 else maximum
            parts.append(line[:cut])
            line = line[cut:].strip()
        if line:
            parts.append(line)
    return parts


def resume_sources(pages: list[str]) -> list[Source]:
    sources = []
    for page, text in enumerate(pages, 1):
        for part in split_text(text):
            if len(part) >= 3:
                sources.append(Source(f'R{len(sources) + 1}', part, page))
    return sources


def job_sources(job: str) -> list[Source]:
    parts = list(dict.fromkeys(part for part in split_text(job, 700) if len(part) >= 3))
    if len(parts) > 60:
        raise ValueError('The job description has too many sections. Keep the responsibilities and requirements only.')
    if not parts:
        raise ValueError('Add at least one job requirement.')
    return [Source(f'J{index}', text) for index, text in enumerate(parts, 1)]


def is_denial(text: str) -> bool:
    return bool(re.search(
        r'\b(?:no|not|without|never|não|nao|nunca|sem)\s+'
        r'(?:(?:tenho|possuo|possui|tem|have|has|had|any|prior|professional|profissional)\s+){0,3}'
        r'(?:experience|knowledge|experi[eê]ncia|conhecimento|dom[ií]nio|worked|used|trabalhei|utilizei)\b',
        text, re.IGNORECASE))


SKILL_PATTERNS = {
    'Java': r'\bjava\b', 'JavaScript': r'\bjavascript\b', 'TypeScript': r'\btypescript\b',
    'Python': r'\bpython\b', 'FastAPI': r'\bfastapi\b', 'SQL': r'\bsql\b',
    'PostgreSQL': r'\b(?:postgresql|postgres)\b', 'MySQL': r'\bmysql\b', 'SQLite': r'\bsqlite\b',
    'HTML': r'\bhtml\b', 'CSS': r'\bcss\b', 'React': r'\breact\b',
    'Git': r'\bgit\b', 'GitHub': r'\bgithub\b', 'Spring Boot': r'\bspring\s+boot\b',
    'object-oriented programming': r'\b(?:oop|poo)\b|object[- ]oriented|orienta(?:cao|da)\s+a?\s*objetos',
}


def named_skills(text: str) -> set[str]:
    normalized = ''.join(char for char in unicodedata.normalize('NFKD', text.lower())
                         if not unicodedata.combining(char))
    return {name for name, pattern in SKILL_PATTERNS.items() if re.search(pattern, normalized)}
