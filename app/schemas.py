from typing import List, Optional
from pydantic import BaseModel, Field


class ChatIn(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=80)
    message: str = Field(..., min_length=1, max_length=2000)
    as_of: Optional[str] = None


class SettingItem(BaseModel):
    name: str
    value: str


class IngestIn(BaseModel):
    text: str = Field(..., min_length=3, max_length=50000)
    doc_id: Optional[str] = None
    title: Optional[str] = None
    doc_type: str = "circular"
    effective_from: Optional[str] = None
    supersedes: Optional[str] = None
    topic: Optional[str] = None
    language: Optional[str] = None
    settings: Optional[List[SettingItem]] = None
