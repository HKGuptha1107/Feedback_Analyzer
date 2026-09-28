"""ProductChange model representing releases, deployments, feature launches, and bug fixes."""

import uuid
from datetime import datetime, timezone, date
from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ProductChange(Base):
    __tablename__ = "product_changes"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(64), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    change_name = Column(String(128), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(64), default="Performance", nullable=False)  # Performance, UI, Feature, BugFix
    release_date = Column(Date, nullable=False, index=True, default=date.today)
    expected_outcome = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    product = relationship("Product", back_populates="product_changes")

    def __repr__(self) -> str:
        return f"<ProductChange(id={self.id}, name={self.change_name}, release_date={self.release_date})>"
