"""Feedback model representing incoming customer feedback across all channels."""

import uuid
from datetime import datetime, timezone, date
from sqlalchemy import Column, String, Text, Integer, Float, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(64), nullable=True, index=True)
    product_id = Column(String(64), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(64), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_name = Column(String(128), default="Anonymous", nullable=False)
    source = Column(String(64), default="App Review", nullable=False, index=True)
    # Sources: "App Review", "Support Ticket", "Survey", "Email", "Feature Request", "Interview", "Social Media"
    
    feedback_text = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # 1 to 5 stars
    feedback_date = Column(Date, nullable=False, index=True, default=date.today)
    
    category = Column(String(64), default="General", nullable=False, index=True)
    # Categories: "Performance", "UI", "Billing", "Notifications", "Integrations", "Reporting", "General"
    
    sentiment = Column(String(32), default="neutral", nullable=False, index=True)
    # Sentiment: "positive", "negative", "neutral"
    
    sentiment_score = Column(Float, default=0.0, nullable=False)  # Normalized -1.0 to 1.0
    
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    product = relationship("Product", back_populates="feedbacks")
    customer = relationship("Customer", back_populates="feedbacks")
    analysis_result = relationship(
        "AnalysisResult",
        back_populates="feedback",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_feedback_prod_date", "product_id", "feedback_date"),
        Index("idx_feedback_prod_sentiment", "product_id", "sentiment"),
        Index("idx_feedback_conversation", "conversation_id", "feedback_date"),
    )

    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, sentiment={self.sentiment}, date={self.feedback_date})>"
