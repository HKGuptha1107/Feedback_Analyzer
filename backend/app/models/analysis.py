"""AnalysisResult model representing AI-triaged feedback enrichment metadata."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    feedback_id = Column(
        String(64),
        ForeignKey("feedbacks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    topic = Column(String(128), nullable=False, index=True)
    urgency = Column(String(32), default="medium", nullable=False)  # low, medium, high, critical
    issue_type = Column(String(32), default="product_issue", nullable=False)
    # issue_type: bug, feature_request, usability, performance, pricing, general
    
    is_recurring = Column(Boolean, default=False, nullable=False)
    short_summary = Column(Text, nullable=False)
    entities = Column(Text, default="[]", nullable=False)  # JSON-serialized list of entities/keywords
    
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    feedback = relationship("Feedback", back_populates="analysis_result")

    def __repr__(self) -> str:
        return f"<AnalysisResult(id={self.id}, topic={self.topic}, urgency={self.urgency})>"
