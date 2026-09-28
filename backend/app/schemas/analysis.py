"""Pydantic schemas for AnalysisResult entity."""

import json
from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class AnalysisResultBase(BaseModel):
    topic: str = Field(..., description="Main topic (e.g. 'file upload speed', 'invoice export')")
    urgency: str = Field("medium", description="Urgency: low, medium, high, critical")
    issue_type: str = Field("product_issue", description="Type: bug, feature_request, usability, performance, pricing, general")
    is_recurring: bool = Field(False, description="Whether this issue matches known historical patterns")
    short_summary: str = Field(..., description="One sentence summary of the feedback")
    entities: List[str] = Field(default_factory=list, description="Key extracted entities and keywords")

    @field_validator("entities", mode="before")
    @classmethod
    def parse_entities(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except Exception:
                # Comma separated fallback
                return [item.strip() for item in v.split(",") if item.strip()]
        elif isinstance(v, (list, tuple)):
            return [str(item) for item in v]
        return []


class AnalysisResultCreate(AnalysisResultBase):
    feedback_id: str


class AnalysisResultRead(AnalysisResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    feedback_id: str
    created_at: datetime
