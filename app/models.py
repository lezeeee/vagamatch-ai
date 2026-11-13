from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal['met', 'partial', 'not_found']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Evidence(StrictModel):
    page: int = Field(ge=1, le=10)
    quote: str = Field(min_length=1)


class RequirementResult(StrictModel):
    requirement: str
    status: Status
    evidence: list[Evidence]
    explanation: str
    suggestion: str


class ReadingSummary(StrictModel):
    pages: int
    ocr_pages: list[int]


class Analysis(StrictModel):
    mode: Literal['ollama'] = 'ollama'
    notice: str = 'AI-assisted comparison. Review the excerpts. Not found means no verified evidence in this resume, not a lack of ability.'
    results: list[RequirementResult]
    warnings: list[str] = Field(default_factory=list)
    reading: ReadingSummary | None = None
    elapsed_seconds: float = 0


class Answer(StrictModel):
    answer: str
    evidence: list[Evidence]
    warnings: list[str] = Field(default_factory=list)
    elapsed_seconds: float = 0


class SourceMatch(StrictModel):
    job_id: str
    status: Status
    evidence_ids: list[str] = Field(max_length=3)


class SourceReport(StrictModel):
    matches: list[SourceMatch] = Field(min_length=1, max_length=30)


class SourceAnswer(StrictModel):
    answer: str = Field(min_length=1, max_length=1400)
    evidence_ids: list[str] = Field(max_length=3)
