"""Pydantic schemas for Feedback entity and ingestion payloads."""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.analysis import AnalysisResultRead


class FeedbackBase(BaseModel):
    customer_name: str = Field("Anonymous", max_length=128)
    source: str = Field("App Review", description="Channel: App Review, Support Ticket, Survey, Email, Feature Request, Interview, Social Media")
    feedback_text: str = Field(..., min_length=3, description="Raw customer feedback text")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Optional star rating from 1 to 5")
    feedback_date: date = Field(default_factory=date.today, description="Date the feedback was submitted")
    category: str = Field("General", description="Category: Performance, UI, Billing, Notifications, Integrations, Reporting, General")
    sentiment: str = Field("neutral", description="Sentiment: positive, negative, neutral")
    sentiment_score: float = Field(0.0, ge=-1.0, le=1.0, description="Normalized sentiment score from -1.0 to 1.0")


class FeedbackCreate(BaseModel):
    conversation_id: Optional[str] = Field(None, description="Conversation or dataset this feedback belongs to")
    product_id: Optional[str] = Field("flowdesk", description="Target product ID (defaults to flowdesk)")
    customer_id: Optional[str] = Field(None, description="Optional customer ID")
    customer_name: Optional[str] = Field("Anonymous", max_length=128)
    source: Optional[str] = Field("App Review")
    feedback_text: str = Field(..., min_length=3)
    rating: Optional[int] = Field(None, ge=1, le=5)
    feedback_date: Optional[date] = Field(default_factory=date.today)
    category: Optional[str] = Field("General")
    sentiment: Optional[str] = Field("neutral")
    sentiment_score: Optional[float] = Field(0.0, ge=-1.0, le=1.0)


class FeedbackRead(FeedbackBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: Optional[str]
    product_id: str
    customer_id: Optional[str]
    created_at: datetime
    analysis_result: Optional[AnalysisResultRead] = None


class FeedbackFilter(BaseModel):
    conversation_id: Optional[str] = None
    conversation_ids: Optional[List[str]] = None
    product_id: Optional[str] = None
    sentiment: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    search: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)


class FeedbackListResponse(BaseModel):
    items: List[FeedbackRead]
    total: int
    page: int
    limit: int
    pages: int


class FeedbackUploadSummary(BaseModel):
    conversation_id: str
    uploaded: int
    processed: int
    successful: int
    failed: int
    errors: List[str] = []
    message: str = "CSV processing complete"
