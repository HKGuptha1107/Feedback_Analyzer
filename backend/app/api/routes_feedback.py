"""API Router for Feedback ingestion, CSV upload, triage analysis, and retrieval."""

from datetime import date
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackRead,
    FeedbackFilter,
    FeedbackListResponse,
    FeedbackUploadSummary,
)
from app.services import feedback_service, triage_service

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
):
    """Manually ingest a single customer feedback item and automatically triage it."""
    try:
        feedback = feedback_service.create_feedback(db, payload)
        return feedback
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to ingest feedback: {str(e)}",
        )


@router.get("", response_model=FeedbackListResponse)
def list_feedbacks(
    conversation_id: Optional[str] = Query(None, description="Filter to one conversation or CSV dataset"),
    conversation_ids: Optional[List[str]] = Query(None, description="Filter to multiple conversation datasets"),
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment (positive, negative, neutral)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    source: Optional[str] = Query(None, description="Filter by feedback channel"),
    search: Optional[str] = Query(None, description="Free-text search in feedback body or customer name"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """Retrieve paginated and filtered customer feedback records with analysis metadata."""
    filters = FeedbackFilter(
        conversation_id=conversation_id,
        conversation_ids=conversation_ids,
        product_id=product_id,
        sentiment=sentiment,
        category=category,
        source=source,
        search=search,
        start_date=start_date,
        end_date=end_date,
        page=page,
        limit=limit,
    )
    items, total = feedback_service.get_feedbacks(db, filters)
    pages = (total + limit - 1) // limit if total > 0 else 1

    return FeedbackListResponse(
        items=[FeedbackRead.model_validate(item) for item in items],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post("/analyze", response_model=Dict[str, Any])
def analyze_unprocessed_feedbacks(
    limit: int = Query(100, ge=1, le=500, description="Maximum items to batch process"),
    db: Session = Depends(get_db),
):
    """Trigger batch triage analysis on pending unprocessed feedback records."""
    summary = triage_service.batch_analyze_unprocessed(db, limit=limit)
    return summary


@router.delete("/conversation/{conversation_id}", response_model=Dict[str, Any])
def delete_conversation_feedback(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    """Delete all feedback imported under one conversation/dataset ID."""
    deleted = feedback_service.delete_feedback_conversation(db, conversation_id)
    return {"conversation_id": conversation_id, "deleted": deleted}


@router.get("/{feedback_id}", response_model=FeedbackRead)
def get_feedback_detail(
    feedback_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve detailed feedback record by its unique ID."""
    fb = feedback_service.get_feedback_by_id(db, feedback_id)
    if not fb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feedback record '{feedback_id}' not found.",
        )
    return FeedbackRead.model_validate(fb)


@router.post("/{feedback_id}/analyze", response_model=FeedbackRead)
def analyze_single_feedback(
    feedback_id: str,
    db: Session = Depends(get_db),
):
    """Trigger or refresh AI triage analysis on a specific feedback record."""
    analysis = triage_service.enrich_feedback_record(db, feedback_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feedback record '{feedback_id}' not found.",
        )
    fb = feedback_service.get_feedback_by_id(db, feedback_id)
    return FeedbackRead.model_validate(fb)


@router.post("/upload", response_model=FeedbackUploadSummary)
async def upload_feedback_csv(
    file: UploadFile = File(..., description="CSV file containing customer feedback"),
    conversation_id: Optional[str] = Query(None, description="Conversation or dataset ID; generated when omitted"),
    product_id: str = Query("flowdesk", description="Target product ID"),
    db: Session = Depends(get_db),
):
    """Upload a CSV file of customer feedback for bulk ingestion and automatic triage."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only CSV (.csv) files are supported.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    summary = feedback_service.process_csv_upload(
        db=db,
        file_bytes=content,
        default_product_id=product_id,
        conversation_id=conversation_id,
        auto_analyze=True,
    )
    return summary
