"""High-level Hindsight Memory Policy and Lifecycle Manager.
Determines WHAT, WHEN, and HOW memories are retained, recalled, and reflected on.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from app.hindsight.client import hindsight_client_instance
from app.models import Feedback, AnalysisResult, ProductChange


class MemoryManager:
    """Orchestrates memory retention policy and knowledge consolidation."""

    def __init__(self, client=None):
        self.client = client or hindsight_client_instance

    def evaluate_and_retain_feedback(
        self,
        feedback: Feedback,
        analysis: AnalysisResult,
    ) -> Optional[Dict[str, Any]]:
        """Evaluate if feedback meets criteria for retention in long-term agent memory.
        
        Policy:
        - Must be a high-urgency bug, recurring issue, or clear feature request.
        - Avoid storing low-signal noise, routine praise, or trivial comments.
        """
        is_high_urgency = analysis.urgency in ("high", "critical")
        is_recurring = analysis.is_recurring
        is_feature = analysis.issue_type == "feature_request"

        if not (is_high_urgency or is_recurring or is_feature):
            return None

        # Build structured observation content
        if is_feature:
            content = f"Customer Feature Request: {analysis.topic}. {analysis.short_summary}"
            mem_type = "feature_request"
        else:
            content = f"Recurring Customer Pain Point: {analysis.topic}. {analysis.short_summary}"
            mem_type = "pain_point"

        tags = ["feedback", mem_type, analysis.topic.lower(), feedback.category.lower()]

        result = self.client.retain(
            content=content,
            context=f"Submitted via {feedback.source} by {feedback.customer_name} on {feedback.feedback_date}",
            tags=tags,
            metadata={
                "feedback_id": feedback.id,
                "category": feedback.category,
                "urgency": analysis.urgency,
                "rating": str(feedback.rating or ""),
            },
            timestamp=datetime.combine(feedback.feedback_date, datetime.min.time(), tzinfo=timezone.utc),
            memory_type=mem_type,
        )
        return result

    def retain_product_change(
        self,
        change: ProductChange,
    ) -> Dict[str, Any]:
        """Retain a product change milestone into memory."""
        content = (
            f"Product Milestone: '{change.change_name}' released on {change.release_date}. "
            f"Category: {change.category}. Description: {change.description}. "
            f"Expected outcome: {change.expected_outcome or 'Not specified'}."
        )
        tags = ["product_change", "release", change.category.lower()]

        return self.client.retain(
            content=content,
            context=f"Product release logged for {change.product_id}",
            tags=tags,
            metadata={
                "product_change_id": change.id,
                "category": change.category,
                "release_date": str(change.release_date),
            },
            timestamp=datetime.combine(change.release_date, datetime.min.time(), tzinfo=timezone.utc),
            memory_type="release_milestone",
        )

    def retain_observed_outcome(
        self,
        change_name: str,
        observation: str,
        release_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retain an observed post-release behavioral shift or resolution."""
        content = f"Historical Release Outcome: Following '{change_name}', {observation}."
        tags = ["outcome", "before_after_analysis", "historical_insight"]

        return self.client.retain(
            content=content,
            context=f"Computed from before/after statistical comparison for release '{change_name}'",
            tags=tags,
            metadata={"release_name": change_name},
            memory_type="observed_outcome",
        )

    def recall(self, query: str, tags: Optional[List[str]] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Search memory bank via TEMPR multi-strategy retrieval."""
        return self.client.recall(query=query, tags=tags, limit=limit)

    def reflect(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Reason across memory bank using Hindsight reasoning engine."""
        return self.client.reflect(query=query, context=context)

    def get_bank_overview(self) -> Dict[str, Any]:
        """Get complete inspector overview of the memory bank."""
        all_memories = self.client.list_all_memories()
        types_breakdown = {}
        for m in all_memories:
            t = m["memory_type"]
            types_breakdown[t] = types_breakdown.get(t, 0) + 1

        return {
            "bank_id": self.client.bank_id,
            "is_live_service": self.client.is_live,
            "total_memories": len(all_memories),
            "memory_types": types_breakdown,
            "memories": all_memories,
        }


# Global singleton instance
memory_manager = MemoryManager()
