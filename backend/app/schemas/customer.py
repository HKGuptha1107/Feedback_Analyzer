"""Pydantic schemas for Customer entity."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, ConfigDict


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    email: Optional[str] = Field(None, max_length=128)
    company: Optional[str] = Field(None, max_length=128)
    tier: str = Field("Pro", description="Customer tier: Free, Pro, Enterprise")


class CustomerCreate(CustomerBase):
    id: Optional[str] = None
    product_id: Optional[str] = None


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: Optional[str]
    created_at: datetime
