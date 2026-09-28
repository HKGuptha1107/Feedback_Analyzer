"""Automated tests for Feedback Triage, topic detection, and batch enrichment."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import Base, get_db
from app.models import Product, Feedback
from app.services.triage_service import classify_text_heuristics


@pytest.fixture(scope="function")
def client():
    """Create a FastAPI test client backed by an isolated in-memory SQLite database."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Seed default product
    seed_db = TestingSessionLocal()
    seed_db.add(Product(id="flowdesk", name="FlowDesk"))
    seed_db.commit()
    seed_db.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def test_classify_text_heuristics_bug():
    """Test heuristic analysis on a performance bug report."""
    text = "Uploading 200MB video presentations fails at 98% consistently. This is a severe blocker!"
    result = classify_text_heuristics(text, rating=1)

    assert result.topic == "file uploads"
    assert result.urgency in ("high", "critical")
    assert result.issue_type == "bug"
    assert result.is_recurring is True
    assert "file upload" in result.entities


def test_classify_text_heuristics_feature_request():
    """Test heuristic analysis on a feature request."""
    text = "Please add dark mode! Late-night triage in FlowDesk is blindingly bright."
    result = classify_text_heuristics(text, rating=3)

    assert result.topic == "dark mode theme"
    assert result.issue_type == "feature_request"
    assert "dark mode" in result.entities


def test_classify_text_heuristics_positive():
    """Test heuristic analysis on positive praise."""
    text = "Love the real-time collaboration canvas. Editing alongside my team is seamless."
    result = classify_text_heuristics(text, rating=5)

    assert result.topic == "real-time collaboration"
    assert result.urgency == "low"
    assert result.issue_type == "positive_praise"


def test_auto_triage_on_single_feedback_submission(client):
    """Test that submitting single feedback automatically generates its AnalysisResult."""
    payload = {
        "product_id": "flowdesk",
        "customer_name": "Marcus Vance",
        "feedback_text": "Uploading large video files gives 504 gateway timeout every single time.",
        "rating": 1,
    }
    res = client.post("/api/feedback", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["analysis_result"] is not None
    ar = data["analysis_result"]
    assert ar["topic"] == "file uploads"
    assert ar["urgency"] in ("high", "critical")
    assert ar["is_recurring"] is True


def test_single_feedback_analyze_endpoint(client):
    """Test POST /api/feedback/{id}/analyze."""
    payload = {
        "product_id": "flowdesk",
        "customer_name": "Sarah Connor",
        "feedback_text": "Need the ability to bulk export monthly invoices to CSV.",
        "rating": 3,
    }
    create_res = client.post("/api/feedback", json=payload)
    fb_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/feedback/{fb_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()
    assert data["analysis_result"]["topic"] == "reporting & export"
    assert data["analysis_result"]["issue_type"] == "feature_request"


def test_batch_analyze_unprocessed_endpoint(client):
    """Test batch processing of feedbacks without analysis."""
    # First, verify analyze endpoint runs cleanly
    batch_res = client.post("/api/feedback/analyze?limit=50")
    assert batch_res.status_code == 200
    summary = batch_res.json()
    assert "analyzed" in summary
    assert "remaining" in summary
