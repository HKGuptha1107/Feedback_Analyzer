"""Pydantic schemas for ProductChange entity."""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ProductChangeBase(BaseModel):
    product_id: str = Field(..., description="ID of the product this change applies to")
    change_name: str = Field(..., min_length=2, max_length=128, description="Release title or feature name")
    description: str = Field(..., min_length=5, description="Full description of release or fix")
    category: str = Field("Performance", description="Category: Performance, UI, Feature, BugFix")
    release_date: date = Field(default_factory=date.today, description="Date the change was deployed")
    expected_outcome: Optional[str] = Field(None, description="Intended outcome or KPI goal")


class ProductChangeCreate(ProductChangeBase):
    id: Optional[str] = None


class ProductChangeRead(ProductChangeBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
