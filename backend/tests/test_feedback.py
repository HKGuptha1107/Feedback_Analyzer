"""Automated integration tests for Feedback Ingestion and CSV Processing endpoints."""

import io
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import Base, get_db
from app.models import Product, Customer


@pytest.fixture(scope="function")
def client():
    """Create a FastAPI test client backed by an isolated in-memory SQLite database with StaticPool."""
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


def test_health_check(client):
    """Test health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_submit_feedback_manual(client):
    """Test manual single feedback submission."""
    payload = {
        "product_id": "flowdesk",
        "customer_name": "Elena Rostova",
        "source": "App Review",
        "feedback_text": "The dark mode theme is clean, but dashboard export to CSV is missing.",
        "rating": 4,
        "category": "UI",
        "sentiment": "positive",
        "sentiment_score": 0.6,
    }
    response = client.post("/api/feedback", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["customer_name"] == "Elena Rostova"
    assert data["category"] == "UI"
    assert data["rating"] == 4
    assert data["sentiment"] == "positive"
    assert "id" in data


def test_list_and_filter_feedback(client):
    """Test listing feedback with pagination, sentiment filtering, and search."""
    # Ingest 3 distinct feedback items
    items = [
        {
            "product_id": "flowdesk",
            "customer_name": "Marcus Vance",
            "source": "Support Ticket",
            "feedback_text": "Critical bug: cannot upload large video attachments!",
            "rating": 1,
            "category": "Performance",
            "sentiment": "negative",
        },
        {
            "product_id": "flowdesk",
            "customer_name": "Chloe Bennett",
            "source": "Survey",
            "feedback_text": "Great collaboration features, love the realtime sync.",
            "rating": 5,
            "category": "Collaboration",
            "sentiment": "positive",
        },
        {
            "product_id": "flowdesk",
            "customer_name": "David Kim",
            "source": "Email",
            "feedback_text": "Notifications are sometimes delayed by 10 minutes.",
            "rating": 3,
            "category": "Notifications",
            "sentiment": "neutral",
        },
    ]
    for item in items:
        res = client.post("/api/feedback", json=item)
        assert res.status_code == 201

    # 1. List all
    res = client.get("/api/feedback")
    assert res.status_code == 200
    assert res.json()["total"] == 3

    # 2. Filter by sentiment
    res = client.get("/api/feedback?sentiment=negative")
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["items"][0]["customer_name"] == "Marcus Vance"

    # 3. Filter by search query
    res = client.get("/api/feedback?search=realtime")
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["items"][0]["customer_name"] == "Chloe Bennett"


def test_get_feedback_by_id(client):
    """Test fetching feedback by ID."""
    payload = {
        "product_id": "flowdesk",
        "customer_name": "Zoe Saldana",
        "feedback_text": "Search indexing takes a few seconds.",
        "rating": 3,
    }
    create_res = client.post("/api/feedback", json=payload)
    assert create_res.status_code == 201
    fb_id = create_res.json()["id"]

    get_res = client.get(f"/api/feedback/{fb_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == fb_id

    # 404 test
    not_found = client.get("/api/feedback/non-existent-id")
    assert not_found.status_code == 404


def test_csv_upload_valid_and_invalid_rows(client):
    """Test CSV file ingestion handling valid and malformed rows."""
    csv_content = """customer_id,customer_name,source,feedback_text,rating,category,sentiment,date
cust-1,Alice Walker,Support Ticket,Uploading large files fails at 90%,1,Performance,negative,2026-10-01
cust-2,Bob Miller,App Review,Love the fast search!,5,Search,positive,2026-10-02
cust-3,Charlie,Survey,,2,UI,negative,2026-10-03
cust-4,Dana Scully,Email,Notification settings are intuitive.,4,Notifications,positive,2026-10-04
"""
    file_bytes = csv_content.encode("utf-8")
    files = {"file": ("test_feedback.csv", io.BytesIO(file_bytes), "text/csv")}

    response = client.post("/api/feedback/upload?product_id=flowdesk", files=files)
    assert response.status_code == 200
    summary = response.json()

    assert summary["uploaded"] == 4
    assert summary["processed"] == 4
    assert summary["successful"] == 3  # row 3 had empty text
    assert summary["failed"] == 1
    assert len(summary["errors"]) == 1

    # Verify rows exist in DB
    list_res = client.get("/api/feedback")
    assert list_res.json()["total"] == 3


def test_csv_uploads_can_be_repeated_with_new_products(client):
    """Test sequential batches with product values that are not pre-seeded."""
    first_csv = "customer_id,customer_name,feedback_text,product\ncust-1,Alice,First batch works,flowdesk\n"
    second_csv = "customer_id,customer_name,feedback_text,product\nC001,Anonymous,Second product batch works,CMF Phone 1\nC002,Anonymous,Another product row,CMF Phone 1\n"

    first_response = client.post(
        "/api/feedback/upload",
        files={"file": ("first.csv", io.BytesIO(first_csv.encode()), "text/csv")},
    )
    second_response = client.post(
        "/api/feedback/upload",
        files={"file": ("second.csv", io.BytesIO(second_csv.encode()), "text/csv")},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["successful"] == 2
    assert second_response.json()["failed"] == 0

    products = client.get("/api/feedback?product_id=CMF%20Phone%201")
    assert products.json()["total"] == 2


def test_csv_conversations_are_isolated_and_deletable(client):
    """Test that separate CSV batches stay isolated and one batch can be removed."""
    first = client.post(
        "/api/feedback/upload",
        files={"file": ("first.csv", io.BytesIO(b"feedback_text\nFirst dataset row\n"), "text/csv")},
    ).json()
    second = client.post(
        "/api/feedback/upload",
        files={"file": ("second.csv", io.BytesIO(b"feedback_text\nSecond dataset row\n"), "text/csv")},
    ).json()

    first_rows = client.get(f"/api/feedback?conversation_id={first['conversation_id']}").json()
    second_rows = client.get(f"/api/feedback?conversation_id={second['conversation_id']}").json()
    combined_rows = client.get(
        f"/api/feedback?conversation_ids={first['conversation_id']}&conversation_ids={second['conversation_id']}"
    ).json()
    assert first_rows["total"] == 1
    assert second_rows["total"] == 1
    assert combined_rows["total"] == 2
    assert first_rows["items"][0]["feedback_text"] != second_rows["items"][0]["feedback_text"]

    deleted = client.delete(f"/api/feedback/conversation/{first['conversation_id']}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] == 1
    assert client.get(f"/api/feedback?conversation_id={first['conversation_id']}").json()["total"] == 0
    assert client.get(f"/api/feedback?conversation_id={second['conversation_id']}").json()["total"] == 1


def test_csv_product_name_matches_existing_product_id_case_insensitively(client):
    """Test product names such as FlowDesk map to the seeded flowdesk product."""
    response = client.post(
        "/api/feedback/upload",
        files={"file": ("named-product.csv", io.BytesIO(b"feedback_text,product\nWorks well,FlowDesk\n"), "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["successful"] == 1
    assert client.get("/api/feedback?product_id=flowdesk").json()["total"] == 1
