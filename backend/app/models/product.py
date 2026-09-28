"""Product model representing tracked software products/services."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    customers = relationship("Customer", back_populates="product", cascade="all, delete-orphan")
    product_changes = relationship("ProductChange", back_populates="product", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name={self.name})>"
