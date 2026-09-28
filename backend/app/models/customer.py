"""Customer model representing feedback authors, users, and accounts."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(64), ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=True, index=True)
    company = Column(String(128), nullable=True)
    tier = Column(String(32), default="Pro", nullable=False)  # Free, Pro, Enterprise
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    product = relationship("Product", back_populates="customers")
    feedbacks = relationship("Feedback", back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, name={self.name}, company={self.company})>"
