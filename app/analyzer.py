"""A deliberately limited local baseline; it makes no external API calls."""
import re
import unicodedata

from app.models import Analysis, Evidence, RequirementResult

STOPWORDS = set('a o as os e de da do das dos em no na nos nas um uma com para por que ter conhecimento conhecimentos requisito requisitos necessario necessaria desejavel basico basica'.split())


def normalize(text: str) -> str:
    text = ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))
    text = re.sub(r'programacao orientada a objetos|orientacao a objetos', 'poo', text)
    return text


def tokens(text: str) -> set[str]:
    return set(re.findall(r'[a-z0-9]+(?:[+#]+)?', normalize(text))) - STOPWORDS


def analyze(pages: list[str], job: str) -> Analysis:
    requirements = [line.strip(' \t-•*\r') for line in re.split(r'[\n;]+', job)]
    requirements = list(dict.fromkeys(line for line in requirements if line))
    if not 1 <= len(requirements) <= 30:
        raise ValueError('Informe de 1 a 30 requisitos, um por linha ou separados por ponto e vírgula.')
    lines = [(number, line.strip()) for number, page in enumerate(pages, 1)
             for line in page.splitlines() if line.strip()]
    results = []
    for requirement in requirements:
        wanted = tokens(requirement)
        evidence = []
        found = set()
        for page, quote in lines:
            # A conservative baseline: never count a line containing a negation as proof.
            if re.search(r'\b(nao|sem|nunca|nenhum|not|no)\b', normalize(quote)):
                continue
            overlap = wanted & tokens(quote)
            if overlap:
                found |= overlap
                evidence.append(Evidence(page=page, quote=quote))
        if wanted and found == wanted:
            status = 'atendido'
            explanation = 'Todos os termos relevantes foram localizados. Confirme o contexto nos trechos.'
            suggestion = 'Se for verdadeiro, complemente com um projeto, sua contribuição e um resultado verificável.'
        elif found:
            status = 'parcialmente_atendido'
            explanation = 'Apenas parte dos termos foi localizada; a demonstração não interpreta equivalências ou nível de experiência.'
            suggestion = 'Revise o requisito e detalhe somente experiências que você realmente possui.'
        else:
            status = 'nao_encontrado'
            explanation = 'Não foi localizada evidência textual suficiente para este requisito.'
            suggestion = 'Se você possui essa experiência, inclua um exemplo real. Caso contrário, considere um projeto de estudo antes de adicioná-la.'
        results.append(RequirementResult(requirement=requirement, status=status, evidence=evidence,
                                         explanation=explanation, suggestion=suggestion))
    return Analysis(results=results)
