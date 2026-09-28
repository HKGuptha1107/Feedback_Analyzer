"""Automated tests for Hindsight Persistent Memory client, manager, and endpoints."""

import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import Base, get_db
from app.models import Feedback, AnalysisResult, ProductChange
from app.hindsight import HindsightMemoryClient, MemoryManager, hindsight_client_instance


@pytest.fixture(autouse=True)
def clean_memory_bank():
    """Clear memory bank before each test."""
    hindsight_client_instance.clear_bank()
    yield
    hindsight_client_instance.clear_bank()


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


def test_hindsight_retain_and_consolidation():
    """Test retain operation and automatic observation consolidation with proof counts."""
    c = HindsightMemoryClient()
    
    # 1. First retention
    r1 = c.retain(
        content="File uploads larger than 100MB timeout at 98%.",
        tags=["performance", "uploads"],
    )
    assert r1["status"] == "retained"
    assert r1["proof_count"] == 1

    # 2. Second retention of identical complaint (should consolidate and increment proofs)
    r2 = c.retain(
        content="File uploads larger than 100MB timeout at 98%.",
        tags=["performance", "timeout"],
    )
    assert r2["status"] == "consolidated"
    assert r2["proof_count"] == 2


def test_hindsight_recall_tempr():
    """Test multi-strategy recall retrieval."""
    c = HindsightMemoryClient()
    c.retain(
        content="File uploads are extremely slow on large files.",
        tags=["uploads", "performance"],
    )
    c.retain(
        content="Dark mode is missing from the dashboard.",
        tags=["ui", "dark_mode"],
    )

    # Search for upload performance
    results = c.recall(query="slow file upload latency", limit=5)
    assert len(results) > 0
    assert "upload" in results[0]["text"].lower()


def test_memory_policy_filtering():
    """Test that MemoryManager retains critical bugs but filters low-signal noise."""
    mgr = MemoryManager()

    # 1. Critical bug feedback -> Should be retained
    fb_bug = Feedback(
        id="fb-1",
        product_id="flowdesk",
        customer_name="Alex",
        feedback_text="504 gateway timeout on file uploads.",
        rating=1,
        category="Performance",
        feedback_date=date(2026, 10, 1),
    )
    ar_bug = AnalysisResult(
        id="ar-1",
        feedback_id="fb-1",
        topic="file uploads",
        urgency="critical",
        issue_type="bug",
        is_recurring=True,
        short_summary="Uploads timeout with 504.",
    )
    res_bug = mgr.evaluate_and_retain_feedback(fb_bug, ar_bug)
    assert res_bug is not None
    assert res_bug["status"] in ("retained", "consolidated")

    # 2. Routine praise feedback -> Should NOT be retained into memory
    fb_praise = Feedback(
        id="fb-2",
        product_id="flowdesk",
        customer_name="Chloe",
        feedback_text="Everything looks great today.",
        rating=5,
        category="General",
        feedback_date=date(2026, 10, 2),
    )
    ar_praise = AnalysisResult(
        id="ar-2",
        feedback_id="fb-2",
        topic="general",
        urgency="low",
        issue_type="positive_praise",
        is_recurring=False,
        short_summary="User likes the app.",
    )
    res_praise = mgr.evaluate_and_retain_feedback(fb_praise, ar_praise)
    assert res_praise is None


def test_retain_product_change():
    """Test storing product change release milestones into memory."""
    mgr = MemoryManager()
    change = ProductChange(
        id="pc-1",
        product_id="flowdesk",
        change_name="Release 3.2: Chunked Upload Optimizer",
        description="Switched to chunked S3 multipart uploads.",
        category="Performance",
        release_date=date(2026, 10, 15),
        expected_outcome="Eliminate upload timeouts.",
    )
    res = mgr.retain_product_change(change)
    assert res["status"] in ("retained", "consolidated")

    # Verify milestone is recallable
    recalled = mgr.recall("Chunked Upload Optimizer")
    assert len(recalled) > 0
    assert "Release 3.2" in recalled[0]["text"]


def test_memory_api_endpoints(client):
    """Test /api/memory inspection, search, retain, and reflect endpoints."""
    # 1. Manual retain via API
    retain_payload = {
        "content": "Customer complaint: Video uploads fail at 99%.",
        "tags": ["uploads", "video", "performance"],
        "memory_type": "pain_point",
    }
    ret_res = client.post("/api/memory/retain", json=retain_payload)
    assert ret_res.status_code == 201

    # 2. Get overview
    overview_res = client.get("/api/memory")
    assert overview_res.status_code == 200
    overview = overview_res.json()
    assert overview["total_memories"] >= 1
    assert "pain_point" in overview["memory_types"]

    # 3. Search via recall
    search_payload = {"query": "video upload failure", "limit": 5}
    search_res = client.post("/api/memory/search", json=search_payload)
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) >= 1
    assert "Video uploads fail" in results[0]["text"]

    # 4. Reflect over memory
    reflect_payload = {"query": "Summarize what problems customers have reported regarding video uploads"}
    ref_res = client.post("/api/memory/reflect", json=reflect_payload)
    assert ref_res.status_code == 200
    assert "reflection" in ref_res.json()
    assert len(ref_res.json()["reflection"]) > 0
