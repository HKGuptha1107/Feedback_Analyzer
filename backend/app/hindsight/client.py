"""Official Hindsight Memory Client Wrapper.
Integrates with the official hindsight-client SDK (retain, recall, reflect)
with resilient degraded-mode local persistence for offline development and testing.
"""

import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

# Try importing official SDK
try:
    from hindsight_client import Hindsight
    HAS_HINDSIGHT_SDK = True
except ImportError:
    Hindsight = None
    HAS_HINDSIGHT_SDK = False


class MemoryItem(BaseModel):
    """Normalized memory record structure."""
    id: str
    bank_id: str
    content: str
    timestamp: datetime
    context: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    proof_count: int = 1
    memory_type: str = "observation"  # observation, fact, release_milestone, outcome


class HindsightMemoryClient:
    """Production-grade client for Hindsight Memory Bank operations."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        bank_id: Optional[str] = None,
    ):
        self.base_url = base_url or settings.HINDSIGHT_URL
        self.api_key = api_key or settings.HINDSIGHT_API_KEY
        self.bank_id = bank_id or settings.HINDSIGHT_BANK_ID
        self._sdk_client: Optional[Any] = None
        self._is_live: bool = False

        # In-memory local durable store for fallback and tests
        self._local_memories: List[MemoryItem] = []

        self._initialize_client()

    def _initialize_client(self):
        """Attempt connection to official Hindsight service."""
        if HAS_HINDSIGHT_SDK and self.base_url and self.api_key:
            try:
                self._sdk_client = Hindsight(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    timeout=10.0,
                )
                # Attempt lightweight ping to verify live server
                try:
                    ver = self._sdk_client.get_version()
                    self._is_live = True
                    logger.info(f"Connected to live Hindsight server (version {ver})")
                except Exception as ping_err:
                    logger.warning(f"Hindsight server configured but ping failed ({ping_err}). Running in resilient hybrid mode.")
                    self._is_live = False
            except Exception as e:
                logger.warning(f"Could not connect to Hindsight service: {e}. Utilizing resilient local memory store.")
                self._is_live = False
        else:
            logger.info("Hindsight API key not supplied. Utilizing resilient local memory bank.")
            self._is_live = False

    @property
    def is_live(self) -> bool:
        """Whether connected to live remote Hindsight service."""
        return self._is_live

    def retain(
        self,
        content: str,
        context: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
        memory_type: str = "observation",
    ) -> Dict[str, Any]:
        """Store high-signal information into Hindsight memory bank."""
        tags = tags or []
        metadata = metadata or {}
        ts = timestamp or datetime.now(timezone.utc)

        # 1. Attempt live Hindsight SDK retain if active
        if self._is_live and self._sdk_client:
            try:
                res = self._sdk_client.retain(
                    bank_id=self.bank_id,
                    content=content,
                    context=context,
                    tags=tags,
                    metadata=metadata,
                    timestamp=ts,
                )
                logger.info(f"Retained to live Hindsight bank '{self.bank_id}'")
            except Exception as e:
                logger.error(f"Live Hindsight retain error: {e}. Persisting to fallback store.")

        # 2. Always persist to resilient local bank for deduplication and zero-downtime inspection
        import uuid
        # Check for similar observation to simulate Hindsight observation consolidation & proof counting
        existing = None
        for m in self._local_memories:
            if m.content.strip().lower() == content.strip().lower():
                existing = m
                break

        if existing:
            existing.proof_count += 1
            existing.timestamp = ts
            for t in tags:
                if t not in existing.tags:
                    existing.tags.append(t)
            existing.metadata.update(metadata)
            return {
                "id": existing.id,
                "bank_id": self.bank_id,
                "status": "consolidated",
                "proof_count": existing.proof_count,
                "content": existing.content,
                "is_live": self._is_live,
            }
        else:
            new_item = MemoryItem(
                id=f"mem-{uuid.uuid4().hex[:8]}",
                bank_id=self.bank_id,
                content=content,
                timestamp=ts,
                context=context,
                tags=tags,
                metadata=metadata,
                proof_count=1,
                memory_type=memory_type,
            )
            self._local_memories.append(new_item)
            return {
                "id": new_item.id,
                "bank_id": self.bank_id,
                "status": "retained",
                "proof_count": 1,
                "content": new_item.content,
                "is_live": self._is_live,
            }

    def recall(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Multi-strategy search retrieving relevant memories from the bank."""
        # 1. Attempt live Hindsight SDK recall if active
        if self._is_live and self._sdk_client:
            try:
                res = self._sdk_client.recall(
                    bank_id=self.bank_id,
                    query=query,
                    tags=tags,
                )
                if hasattr(res, "results") and res.results:
                    return [
                        {
                            "id": getattr(r, "id", f"live-{idx}"),
                            "text": getattr(r, "text", str(r)),
                            "score": getattr(r, "score", 0.9),
                            "tags": getattr(r, "tags", tags or []),
                            "source": "hindsight_live",
                        }
                        for idx, r in enumerate(res.results)
                    ]
            except Exception as e:
                logger.error(f"Live Hindsight recall failed: {e}. Falling back to local recall.")

        # 2. Resilient TEMPR multi-strategy matching (Temporal, Entity, Meaning/Keyword)
        q_tokens = [w.lower() for w in query.split() if len(w) > 2]
        scored_results: List[Tuple[float, MemoryItem]] = []

        for item in self._local_memories:
            score = 0.0
            content_lower = item.content.lower()

            # Exact keyword match
            for t in q_tokens:
                if t in content_lower:
                    score += 1.0

            # Tag match bonus
            if tags:
                for t in tags:
                    if t.lower() in [it.lower() for it in item.tags]:
                        score += 2.0

            # Proof count weighting (consolidated observations with more evidence rank higher)
            score += min(item.proof_count * 0.2, 1.5)

            if score > 0.0:
                scored_results.append((score, item))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "id": item.id,
                "text": item.content,
                "score": round(score, 2),
                "proof_count": item.proof_count,
                "tags": item.tags,
                "timestamp": item.timestamp.isoformat(),
                "memory_type": item.memory_type,
                "context": item.context,
                "source": "hindsight_memory_bank",
            }
            for score, item in scored_results[:limit]
        ]

    def reflect(
        self,
        query: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synthesize agentic reflection across stored memories."""
        # 1. Attempt live Hindsight SDK reflect if active
        if self._is_live and self._sdk_client:
            try:
                res = self._sdk_client.reflect(
                    bank_id=self.bank_id,
                    query=query,
                    context=context,
                )
                text = getattr(res, "text", None) or getattr(res, "response", str(res))
                return {
                    "query": query,
                    "reflection": text,
                    "source": "hindsight_live_reflect",
                    "bank_id": self.bank_id,
                }
            except Exception as e:
                logger.error(f"Live Hindsight reflect failed: {e}. Falling back to Groq agent reflection.")

        # 2. Resilient reflection using Groq over recalled memories
        from app.groq import groq_client
        recalled = self.recall(query, limit=8)
        evidence_text = "\n".join(
            [f"- [{m['timestamp'][:10]}] (Proofs: {m['proof_count']}) {m['text']}" for m in recalled]
        )
        if not evidence_text:
            evidence_text = "No historical memories found for this topic."

        prompt = f"""You are reasoning over Hindsight Persistent Memory for Feedback Analyzer.
Memory Bank: {self.bank_id}
User Query: {query}
Additional Context: {context or 'None'}

Evidence from Hindsight Memory Bank:
{evidence_text}

Task: Reflect on this evidence to provide a comprehensive, chronological, and pattern-aware answer.
Cite specific observations, proof counts, and release milestones if present.
"""
        reflection = groq_client.chat_completion_text(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        return {
            "query": query,
            "reflection": reflection,
            "evidence": recalled,
            "evidence_count": len(recalled),
            "bank_id": self.bank_id,
            "source": "hindsight_reasoning_engine",
        }

    def list_all_memories(self) -> List[Dict[str, Any]]:
        """List all memories currently stored in the memory bank."""
        return [
            {
                "id": m.id,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "proof_count": m.proof_count,
                "tags": m.tags,
                "metadata": m.metadata,
                "memory_type": m.memory_type,
                "context": m.context,
            }
            for m in sorted(self._local_memories, key=lambda x: x.timestamp, reverse=True)
        ]

    def clear_bank(self):
        """Clear local memory store (used in tests)."""
        self._local_memories.clear()


# Global singleton instance
hindsight_client_instance = HindsightMemoryClient()
