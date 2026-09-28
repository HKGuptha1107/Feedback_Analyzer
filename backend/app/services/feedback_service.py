"""Feedback service handling ingestion, CSV parsing, validation, and querying."""

import io
import csv
import uuid
import json
from datetime import datetime, date
from typing import List, Tuple, Optional, Dict, Any, Set
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload
from app.models import Feedback, Product, Customer, AnalysisResult
from app.schemas.feedback import FeedbackCreate, FeedbackFilter, FeedbackUploadSummary
from app.services import triage_service


def ensure_default_product(db: Session, product_id: str = "flowdesk", name: str = "Feedback Analyzer") -> Product:
    """Ensure that the target product exists in the database, creating it if missing."""
    product = db.query(Product).filter_by(id=product_id).first()
    if not product:
        product = Product(
            id=product_id,
            name=name,
            description="Feedback Analyzer customer feedback intelligence workspace.",
        )
        db.add(product)
        db.commit()
        db.refresh(product)
    return product


def resolve_product_id(db: Session, product_value: str) -> str:
    """Treat CSV product names and IDs case-insensitively without creating aliases."""
    normalized = product_value.strip()
    existing_id = db.query(Product).filter(Product.id == normalized).first()
    if existing_id:
        return existing_id.id
    existing_name = db.query(Product).filter(func.lower(Product.name) == normalized.lower()).first()
    return existing_name.id if existing_name else normalized


def create_feedback(db: Session, payload: FeedbackCreate) -> Feedback:
    """Ingest a single feedback item into the database with validation, normalization, and automatic triage."""
    product_id = payload.product_id or "flowdesk"
    ensure_default_product(db, product_id=product_id)

    # Resolve or create customer if provided
    customer_id = payload.customer_id
    if customer_id:
        cust = db.query(Customer).filter_by(id=customer_id).first()
        if not cust:
            cust = Customer(
                id=customer_id,
                product_id=product_id,
                name=payload.customer_name or "Anonymous",
            )
            db.add(cust)
            db.commit()

    # Determine default sentiment and score if not explicitly set
    sentiment = (payload.sentiment or "neutral").lower()
    score = payload.sentiment_score if payload.sentiment_score is not None else 0.0

    if payload.rating is not None and payload.sentiment is None:
        if payload.rating >= 4:
            sentiment = "positive"
            score = 0.8
        elif payload.rating <= 2:
            sentiment = "negative"
            score = -0.8
        else:
            sentiment = "neutral"
            score = 0.0

    feedback_id = str(uuid.uuid4())
    feedback = Feedback(
        id=feedback_id,
        conversation_id=payload.conversation_id,
        product_id=product_id,
        customer_id=customer_id,
        customer_name=payload.customer_name or "Anonymous",
        source=payload.source or "App Review",
        feedback_text=payload.feedback_text.strip(),
        rating=payload.rating,
        feedback_date=payload.feedback_date or date.today(),
        category=payload.category or "General",
        sentiment=sentiment,
        sentiment_score=score,
    )
    db.add(feedback)
    db.commit()

    # Automatic analysis enrichment
    analysis_data = triage_service.classify_text_heuristics(
        text=feedback.feedback_text,
        rating=feedback.rating,
        category_hint=feedback.category,
    )
    analysis = AnalysisResult(
        id=str(uuid.uuid4()),
        feedback_id=feedback_id,
        topic=analysis_data.topic,
        urgency=analysis_data.urgency,
        issue_type=analysis_data.issue_type,
        is_recurring=analysis_data.is_recurring,
        short_summary=analysis_data.short_summary,
        entities=json.dumps(analysis_data.entities),
    )
    db.add(analysis)
    db.commit()
    triage_service._retain_high_signal_memory(feedback, analysis)
    db.refresh(feedback)
    return feedback


def get_feedbacks(db: Session, filters: FeedbackFilter) -> Tuple[List[Feedback], int]:
    """Retrieve paginated and filtered feedback records."""
    query = db.query(Feedback).options(joinedload(Feedback.analysis_result))

    if filters.product_id:
        query = query.filter(Feedback.product_id == filters.product_id)
    if filters.conversation_id:
        query = query.filter(Feedback.conversation_id == filters.conversation_id)
    if filters.conversation_ids:
        query = query.filter(Feedback.conversation_id.in_(filters.conversation_ids))
    if filters.sentiment:
        query = query.filter(Feedback.sentiment == filters.sentiment.lower())
    if filters.category:
        query = query.filter(Feedback.category.ilike(f"%{filters.category}%"))
    if filters.source:
        query = query.filter(Feedback.source == filters.source)
    if filters.start_date:
        query = query.filter(Feedback.feedback_date >= filters.start_date)
    if filters.end_date:
        query = query.filter(Feedback.feedback_date <= filters.end_date)
    if filters.search:
        term = f"%{filters.search.strip()}%"
        query = query.filter(
            or_(
                Feedback.feedback_text.ilike(term),
                Feedback.customer_name.ilike(term),
                Feedback.category.ilike(term),
            )
        )

    total = query.count()
    offset = (filters.page - 1) * filters.limit
    items = (
        query.order_by(Feedback.feedback_date.desc(), Feedback.created_at.desc())
        .offset(offset)
        .limit(filters.limit)
        .all()
    )
    return items, total


def get_feedback_by_id(db: Session, feedback_id: str) -> Optional[Feedback]:
    """Retrieve a single feedback record by primary key."""
    return (
        db.query(Feedback)
        .options(joinedload(Feedback.analysis_result))
        .filter(Feedback.id == feedback_id)
        .first()
    )


def delete_feedback_conversation(db: Session, conversation_id: str) -> int:
    """Delete all feedback and analysis records belonging to one imported dataset."""
    feedbacks = db.query(Feedback).filter(Feedback.conversation_id == conversation_id).all()
    if not feedbacks:
        return 0
    customer_ids = {feedback.customer_id for feedback in feedbacks if feedback.customer_id}
    for feedback in feedbacks:
        db.delete(feedback)
    db.commit()
    for customer_id in customer_ids:
        if not db.query(Feedback).filter(Feedback.customer_id == customer_id).first():
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if customer:
                db.delete(customer)
    db.commit()
    return len(feedbacks)


def _parse_date(date_str: str) -> date:
    """Helper to parse varied date string formats safely."""
    date_str = date_str.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(date_str[:10]).date()
    except Exception:
        return date.today()


def _normalize_sentiment(val: str, rating: Optional[int]) -> Tuple[str, float]:
    """Normalize sentiment and calculate a consistent score."""
    val_clean = (val or "").strip().lower()
    if val_clean in ("positive", "pos", "+1"):
        return "positive", 0.8
    elif val_clean in ("negative", "neg", "-1"):
        return "negative", -0.8
    elif val_clean in ("neutral", "neu", "0"):
        return "neutral", 0.0

    if rating is not None:
        if rating >= 4:
            return "positive", 0.8
        elif rating <= 2:
            return "negative", -0.8
    return "neutral", 0.0


def process_csv_upload(
    db: Session,
    file_bytes: bytes,
    default_product_id: str = "flowdesk",
    conversation_id: Optional[str] = None,
    auto_analyze: bool = True,
) -> FeedbackUploadSummary:
    """Validate, parse, and ingest bulk customer feedback from a CSV file."""
    conversation_id = conversation_id or str(uuid.uuid4())

    if not file_bytes:
        return FeedbackUploadSummary(
            conversation_id=conversation_id,
            uploaded=0,
            processed=0,
            successful=0,
            failed=0,
            errors=["Uploaded file is empty."],
            message="No data uploaded",
        )

    decoded_text = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            decoded_text = file_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if not decoded_text:
        return FeedbackUploadSummary(
            conversation_id=conversation_id,
            uploaded=0,
            processed=0,
            successful=0,
            failed=0,
            errors=["Unable to decode CSV file. Please upload a standard UTF-8 encoded file."],
            message="Encoding failure",
        )

    reader = csv.DictReader(io.StringIO(decoded_text))
    if not reader.fieldnames:
        return FeedbackUploadSummary(
            conversation_id=conversation_id,
            uploaded=0,
            processed=0,
            successful=0,
            failed=0,
            errors=["CSV file must contain a header row."],
            message="Invalid CSV format",
        )

    header_map: Dict[str, str] = {}
    for h in reader.fieldnames:
        key = h.strip().lower().replace(" ", "_")
        header_map[key] = h

    def get_val(row: Dict[str, Any], aliases: List[str], default: str = "") -> str:
        for alias in aliases:
            if alias in header_map:
                val = row.get(header_map[alias])
                if val is not None and str(val).strip():
                    return str(val).strip()
        return default

    ensure_default_product(db, product_id=default_product_id)

    existing_cust_ids: Set[str] = {c[0] for c in db.query(Customer.id).all()}
    customers_to_create: Dict[str, Customer] = {}

    total_rows = 0
    successful = 0
    failed = 0
    errors: List[str] = []
    feedbacks_to_insert: List[Feedback] = []
    product_ids: Set[str] = set()

    for row_idx, row in enumerate(reader, start=2):
        total_rows += 1
        text = get_val(row, ["feedback_text", "feedback", "text", "comment", "review", "message"])
        if not text or len(text) < 3:
            failed += 1
            if len(errors) < 20:
                errors.append(f"Row {row_idx}: Feedback text is missing or too short (min 3 chars).")
            continue

        cust_id = get_val(row, ["customer_id", "user_id", "cust_id"]) or None
        cust_name = get_val(row, ["customer_name", "customer", "user", "name", "author"], default="Anonymous")
        source = get_val(row, ["source", "channel"], default="App Review")
        category = get_val(row, ["category", "feature", "module", "topic"], default="General")
        prod_id = resolve_product_id(db, get_val(row, ["product_id", "product"], default=default_product_id))
        product_ids.add(prod_id)

        if cust_id and cust_id not in existing_cust_ids and cust_id not in customers_to_create:
            customers_to_create[cust_id] = Customer(
                id=cust_id,
                product_id=prod_id,
                name=cust_name,
            )

        rating_raw = get_val(row, ["rating", "stars", "score"])
        rating: Optional[int] = None
        if rating_raw:
            try:
                r_int = int(float(rating_raw))
                if 1 <= r_int <= 5:
                    rating = r_int
            except ValueError:
                pass

        date_raw = get_val(row, ["feedback_date", "date", "created_at", "timestamp"])
        feedback_date = _parse_date(date_raw) if date_raw else date.today()

        sentiment_raw = get_val(row, ["sentiment"])
        sentiment, score = _normalize_sentiment(sentiment_raw, rating)

        fb = Feedback(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            product_id=prod_id,
            customer_id=cust_id,
            customer_name=cust_name,
            source=source,
            feedback_text=text,
            rating=rating,
            feedback_date=feedback_date,
            category=category,
            sentiment=sentiment,
            sentiment_score=score,
        )
        feedbacks_to_insert.append(fb)
        successful += 1

    # A batch may introduce products that are not in the default workspace.
    # Create those parent rows before inserting customers with foreign keys to them.
    for product_id in product_ids:
        if product_id != default_product_id:
            ensure_default_product(db, product_id=product_id, name=product_id)

    if customers_to_create:
        db.bulk_save_objects(list(customers_to_create.values()))
        db.commit()

    if feedbacks_to_insert:
        db.bulk_save_objects(feedbacks_to_insert)
        db.commit()

        # Batch auto-analyze newly uploaded records
        if auto_analyze:
            triage_service.batch_analyze_unprocessed(db, limit=len(feedbacks_to_insert))

    return FeedbackUploadSummary(
        conversation_id=conversation_id,
        uploaded=total_rows,
        processed=total_rows,
        successful=successful,
        failed=failed,
        errors=errors,
        message=f"Successfully ingested and triaged {successful} of {total_rows} feedback records.",
    )
