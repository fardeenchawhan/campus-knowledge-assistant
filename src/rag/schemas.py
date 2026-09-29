from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=2000,
    )


class SourceResponse(BaseModel):
    source_number: int
    document: str
    version: int
    page: int | None = None
    section: str | None = None
    chunk_id: int


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]