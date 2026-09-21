from datetime import datetime

from pydantic import BaseModel


class DocumentAdminResponse(BaseModel):
    id: int
    document_key: str
    title: str
    source: str
    current_version: int | None
    created_at: datetime
    updated_at: datetime