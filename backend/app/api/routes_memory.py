"""API Router for Hindsight Memory Bank inspection, recall, and reflection."""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.hindsight import memory_manager

router = APIRouter(prefix="/api/memory", tags=["Hindsight Memory"])


class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Search query for TEMPR memory recall")
    tags: Optional[List[str]] = Field(None, description="Optional tag filters")
    limit: int = Field(5, ge=1, le=20, description="Max memories to retrieve")


class MemoryReflectRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Complex analytical question requiring memory reflection")
    context: Optional[str] = Field(None, description="Additional product context")


class MemoryRetainRequest(BaseModel):
    content: str = Field(..., min_length=5, description="High-signal memory observation or milestone")
    context: Optional[str] = Field(None, description="Context of origin")
    tags: Optional[List[str]] = Field(default_factory=list, description="Associated tags")
    memory_type: str = Field("observation", description="Memory type: observation, release_milestone, feature_request, pain_point")


@router.get("", response_model=Dict[str, Any])
def get_memory_bank_overview():
    """Retrieve complete overview of memories, proof counts, and memory bank status."""
    return memory_manager.get_bank_overview()


@router.post("/search", response_model=List[Dict[str, Any]])
def search_memory(payload: MemorySearchRequest):
    """Perform multi-strategy TEMPR search to recall relevant historical memories."""
    return memory_manager.recall(
        query=payload.query,
        tags=payload.tags,
        limit=payload.limit,
    )


@router.post("/reflect", response_model=Dict[str, Any])
def reflect_over_memory(payload: MemoryReflectRequest):
    """Synthesize reasoning across historical memories using Hindsight reflection."""
    return memory_manager.reflect(
        query=payload.query,
        context=payload.context,
    )


@router.post("/retain", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def retain_manual_memory(payload: MemoryRetainRequest):
    """Manually retain a memory or milestone into the Hindsight memory bank."""
    return memory_manager.client.retain(
        content=payload.content,
        context=payload.context,
        tags=payload.tags,
        memory_type=payload.memory_type,
    )
