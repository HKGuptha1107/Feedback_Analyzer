"""Automated tests for database engine, models, and schema validation."""

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Product, Customer, ProductChange, Feedback, AnalysisResult
from app.schemas import (
    ProductCreate,
    ProductRead,
    CustomerCreate,
    CustomerRead,
    ProductChangeCreate,
    ProductChangeRead,
    FeedbackCreate,
    FeedbackRead,
    AnalysisResultCreate,
    AnalysisResultRead,
)


@pytest.fixture(scope="function")
def db_session():
    """Create an isolated in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_create_and_query_product(db_session):
    """Test product creation and Pydantic schema serialization."""
    prod_data = ProductCreate(
        id="flowdesk",
        name="FlowDesk Productivity Suite",
        description="Fictional collaboration and productivity platform.",
    )
    product = Product(
        id=prod_data.id,
        name=prod_data.name,
        description=prod_data.description,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    queried = db_session.query(Product).filter_by(id="flowdesk").first()
    assert queried is not None
    assert queried.name == "FlowDesk Productivity Suite"

    # Schema serialization check
    read_dto = ProductRead.model_validate(queried)
    assert read_dto.id == "flowdesk"
    assert read_dto.name == "FlowDesk Productivity Suite"


def test_create_customer(db_session):
    """Test customer creation linked to a product."""
    product = Product(id="flowdesk", name="FlowDesk")
    db_session.add(product)
    db_session.commit()

    customer = Customer(
        id="cust-001",
        product_id="flowdesk",
        name="Sarah Connor",
        email="sarah@cyberdyne.com",
        company="Cyberdyne Systems",
        tier="Enterprise",
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    assert customer.id == "cust-001"
    assert customer.product.name == "FlowDesk"


def test_create_product_change(db_session):
    """Test logging a product change milestone."""
    product = Product(id="flowdesk", name="FlowDesk")
    db_session.add(product)
    db_session.commit()

    change = ProductChange(
        id="pc-302",
        product_id="flowdesk",
        change_name="Release 3.2: Chunked Upload Optimizer",
        description="Overhauled file upload pipeline using chunked multipart S3 uploads.",
        category="Performance",
        release_date=date(2026, 10, 15),
        expected_outcome="Reduce large file upload latency and eliminate timeouts.",
    )
    db_session.add(change)
    db_session.commit()
    db_session.refresh(change)

    assert change.category == "Performance"
    assert change.release_date == date(2026, 10, 15)

    change_read = ProductChangeRead.model_validate(change)
    assert change_read.change_name == "Release 3.2: Chunked Upload Optimizer"


def test_create_feedback_with_analysis(db_session):
    """Test inserting feedback and linked analysis enrichment result."""
    product = Product(id="flowdesk", name="FlowDesk")
    customer = Customer(id="cust-100", product_id="flowdesk", name="Alex Rivera")
    db_session.add_all([product, customer])
    db_session.commit()

    feedback = Feedback(
        id="fb-1001",
        product_id="flowdesk",
        customer_id="cust-100",
        customer_name="Alex Rivera",
        source="Support Ticket",
        feedback_text="Uploading 200MB video presentations fails at 98% consistently.",
        rating=1,
        feedback_date=date(2026, 10, 1),
        category="Performance",
        sentiment="negative",
        sentiment_score=-0.85,
    )
    db_session.add(feedback)
    db_session.commit()
    db_session.refresh(feedback)

    analysis = AnalysisResult(
        id="ar-1001",
        feedback_id="fb-1001",
        topic="file upload failure",
        urgency="high",
        issue_type="bug",
        is_recurring=True,
        short_summary="Customer experiences persistent 98% timeouts when uploading large videos.",
        entities='["file upload", "video presentation", "timeout"]',
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(feedback)

    # Query with relationships
    queried_fb = db_session.query(Feedback).filter_by(id="fb-1001").first()
    assert queried_fb is not None
    assert queried_fb.analysis_result is not None
    assert queried_fb.analysis_result.urgency == "high"
    assert queried_fb.analysis_result.is_recurring is True
    assert queried_fb.customer.name == "Alex Rivera"

    # Validate Pydantic serialization
    fb_read = FeedbackRead.model_validate(queried_fb)
    assert fb_read.sentiment == "negative"
    assert fb_read.analysis_result is not None
    assert fb_read.analysis_result.topic == "file upload failure"
