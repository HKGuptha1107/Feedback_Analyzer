"""Groq LLM package exporting client and prompts."""

from app.groq.client import GroqClient, groq_client
from app.groq.prompts import (
    PRODUCT_INTELLIGENCE_AGENT_PROMPT,
    FEEDBACK_TRIAGE_LLM_PROMPT,
    BEFORE_AFTER_SYNTHESIS_PROMPT,
    EMERGING_ISSUES_EXPLANATION_PROMPT,
)

__all__ = [
    "GroqClient",
    "groq_client",
    "PRODUCT_INTELLIGENCE_AGENT_PROMPT",
    "FEEDBACK_TRIAGE_LLM_PROMPT",
    "BEFORE_AFTER_SYNTHESIS_PROMPT",
    "EMERGING_ISSUES_EXPLANATION_PROMPT",
]
