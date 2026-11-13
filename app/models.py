from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Evidence(BaseModel):
    model_config = ConfigDict(extra='forbid')
    page: int = Field(ge=1, le=10)
    quote: str = Field(min_length=3, max_length=1500)


class RequirementResult(BaseModel):
    requirement: str
    status: Literal['atendido', 'parcialmente_atendido', 'nao_encontrado']
    evidence: list[Evidence]
    explanation: str
    suggestion: str


class Analysis(BaseModel):
    mode: Literal['demo', 'openai', 'ollama'] = 'demo'
    notice: str = (
        'Demonstração por palavras-chave, sem IA. As categorias indicam apenas '
        'correspondência textual, não comprovam competências nem chance de contratação. '
        'Revise as evidências. Não encontrado não significa que você não sabe.'
    )
    results: list[RequirementResult]


class AIRequirement(BaseModel):
    model_config = ConfigDict(extra='forbid')
    requirement: str = Field(min_length=3, max_length=1000)
    status: Literal['atendido', 'parcialmente_atendido', 'nao_encontrado']
    evidence: list[Evidence] = Field(max_length=5)
    explanation: str = Field(min_length=3, max_length=800)


class AIReport(BaseModel):
    model_config = ConfigDict(extra='forbid')
    results: list[AIRequirement] = Field(min_length=1, max_length=30)


class AIAnswer(BaseModel):
    model_config = ConfigDict(extra='forbid')
    answer: str = Field(min_length=3, max_length=2500)
    evidence: list[Evidence] = Field(max_length=5)


class Answer(AIAnswer):
    mode: Literal['openai', 'ollama'] = 'ollama'
