"""Automated tests for Groq LLM Client, model fallback, and prompt rendering."""

import pytest
from app.groq import (
    groq_client,
    GroqClient,
    PRODUCT_INTELLIGENCE_AGENT_PROMPT,
    BEFORE_AFTER_SYNTHESIS_PROMPT,
)


def test_groq_client_configured():
    """Verify that GroqClient detects configured API key."""
    assert groq_client.is_configured is True
    assert groq_client.primary_model == "openai/gpt-oss-120b"
    assert groq_client.fallback_model == "openai/gpt-oss-20b"


def test_groq_test_connection():
    """Verify live connectivity and ping response from Groq API."""
    conn_info = groq_client.test_connection()
    assert conn_info["status"] == "connected"
    assert "latency_ms" in conn_info
    assert conn_info["latency_ms"] > 0
    assert len(conn_info["response"]) > 0


def test_groq_chat_completion_text():
    """Test standard chat completion text response using primary model."""
    prompt = [{"role": "user", "content": "What is the capital of France? Answer with one word."}]
    res = groq_client.chat_completion_text(messages=prompt, max_tokens=256)
    assert "paris" in res.lower()


def test_groq_model_fallback():
    """Test that specifying an invalid primary model automatically triggers the fallback model."""
    client = GroqClient(
        model="nonexistent-dummy-model-9999",
        fallback_model="openai/gpt-oss-20b",
    )
    prompt = [{"role": "user", "content": "Say hello."}]
    res = client.chat_completion_text(messages=prompt, max_tokens=256)
    assert len(res.strip()) > 0


def test_prompt_rendering():
    """Verify before-after comparison prompt formats correctly."""
    rendered = BEFORE_AFTER_SYNTHESIS_PROMPT.format(
        change_name="Release 3.2: Chunked Upload Optimizer",
        category="Performance",
        release_date="2026-10-15",
        expected_outcome="Reduce latency and eliminate timeouts",
        pre_total=100,
        pre_negative=55,
        pre_positive=30,
        pre_avg_rating=2.1,
        target_topic="file uploads",
        pre_topic_mentions=42,
        post_total=90,
        post_negative=10,
        post_positive=65,
        post_avg_rating=4.3,
        post_topic_mentions=4,
        memory_context="Recurring customer complaint: Uploads fail at 98%.",
    )
    assert "Release 3.2: Chunked Upload Optimizer" in rendered
    assert "pre_topic_mentions=42" not in rendered
    assert "42 mentions" in rendered
    assert "4 mentions" in rendered
