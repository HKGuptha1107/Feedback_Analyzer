"""Pydantic schemas for Product entity."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=128, description="Unique product name")
    description: Optional[str] = Field(None, description="Detailed product description")


class ProductCreate(ProductBase):
    id: Optional[str] = Field(None, description="Optional custom identifier (e.g. flowdesk)")


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
