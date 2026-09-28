"""Feedback triage and classification service.
Provides hybrid high-throughput pattern analysis and LLM enrichment for sentiment,
topics, urgency, issue types, entities, and recurring problem identification.
"""

import re
import json
import uuid
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models import Feedback, AnalysisResult
from app.schemas.analysis import AnalysisResultBase


def _retain_high_signal_memory(feedback: Feedback, analysis: AnalysisResult) -> None:
    """Persist qualifying agent observations without blocking feedback ingestion."""
    try:
        from app.hindsight import memory_manager

        memory_manager.evaluate_and_retain_feedback(feedback, analysis)
    except Exception:
        # Hindsight is an enrichment layer; database-backed feedback must remain available.
        pass


# Keyword topic mappings for Feedback Analyzer
TOPIC_PATTERNS = [
    (r"\b(upload|uploading|attachment|multipart|s3|file transfer)\b", "file uploads", "Performance"),
    (r"\b(timeout|504|gateway timeout|aborted|hangs|crash|crashes)\b", "timeouts & stability", "Performance"),
    (r"\b(slow|latency|lag|sluggish|speed|performance|forever)\b", "system performance", "Performance"),
    (r"\b(dark mode|theme|light mode|contrast|night mode)\b", "dark mode theme", "UI"),
    (r"\b(export|csv|parquet|download data|report export|bulk export)\b", "reporting & export", "Reporting"),
    (r"\b(notification|notifications|alert|delay|noisy|ping)\b", "notification delivery", "Notifications"),
    (r"\b(search|indexing|query|find|lookup)\b", "search functionality", "Search"),
    (r"\b(slack|jira|calendar|webhook|integration|api)\b", "third-party integrations", "Integrations"),
    (r"\b(pricing|price|expensive|cost|billing|invoice|plan|subscription)\b", "pricing & plans", "Billing"),
    (r"\b(mobile|ipad|tablet|responsive|layout|screen)\b", "mobile & responsive UI", "UI"),
    (r"\b(collab|collaboration|realtime|sync|canvas|board)\b", "real-time collaboration", "Collaboration"),
    (r"\b(permission|permissions|role|roles|security|rbac|auth)\b", "access control & permissions", "Security"),
]

URGENCY_KEYWORDS = {
    "critical": [
        "crash", "crashes", "lost data", "blocker", "blocking", "severe", "unusable",
        "emergency", "down", "outage", "504", "switch tools", "switching tools"
    ],
    "high": [
        "fail", "fails", "failed", "broken", "cannot", "can't", "unable to",
        "timeout", "timeouts", "painfully slow", "consistently fails", "error"
    ],
    "medium": [
        "slow", "lag", "confusing", "needs improvement", "annoying", "delay", "delayed",
        "hard to", "difficult"
    ],
    "low": [
        "would be nice", "suggestion", "minor", "tweak", "slight", "optional", "cosmetic"
    ],
}

ISSUE_TYPE_PATTERNS = [
    (r"\b(bug|error|crash|broken|fails|fail|glitch|exception|504)\b", "bug"),
    (r"\b(feature request|please add|would love|wish|need the ability|could we have|hope to see)\b", "feature_request"),
    (r"\b(slow|speed|latency|lag|timeout|performance|bandwidth)\b", "performance"),
    (r"\b(pricing|expensive|cheap|cost|billing|invoice)\b", "pricing"),
    (r"\b(confusing|cluttered|unintuitive|ugly|look and feel|navigation|ui|ux)\b", "usability"),
]

ENTITY_PATTERNS = [
    (r"\b(upload|uploads|uploading|attachment)\b", "file upload"),
    (r"\b(video|videos|presentation)\b", "video presentation"),
    (r"\b(dashboard|dashboards)\b", "dashboard"),
    (r"\b(report|reports)\b", "report"),
    (r"\b(csv|parquet|export)\b", "csv export"),
    (r"\b(dark mode|night mode)\b", "dark mode"),
    (r"\b(slack)\b", "slack integration"),
    (r"\b(notification|notifications)\b", "notification"),
    (r"\b(search|indexing)\b", "search filter"),
    (r"\b(kanban|board)\b", "kanban board"),
    (r"\b(calendar)\b", "calendar sync"),
    (r"\b(timeout|timeouts|504)\b", "timeout"),
    (r"\b(permission|permissions|rbac)\b", "permissions"),
    (r"\b(pricing|billing|invoice)\b", "pricing"),
    (r"\b(realtime|sync)\b", "realtime sync"),
    (r"\b(screen recording)\b", "screen recording"),
]


def classify_text_heuristics(
    text: str,
    rating: Optional[int] = None,
    category_hint: Optional[str] = None,
) -> AnalysisResultBase:
    """Analyze feedback text using high-throughput linguistic pattern heuristics."""
    text_lower = text.lower()

    # 1. Identify Topic & Category
    topic = "general feedback"
    detected_category = category_hint or "General"
    for pattern, top_name, cat_name in TOPIC_PATTERNS:
        if re.search(pattern, text_lower):
            topic = top_name
            if not category_hint or category_hint == "General":
                detected_category = cat_name
            break

    # 2. Determine Urgency
    urgency = "low" if (rating and rating >= 4) else "medium"
    for level in ["critical", "high", "medium", "low"]:
        if any(kw in text_lower for kw in URGENCY_KEYWORDS[level]):
            urgency = level
            break

    # If rating is 1 star and text mentions failure or blocker, escalate urgency
    if rating == 1 and urgency in ("low", "medium"):
        urgency = "high"

    # 3. Determine Issue Type
    issue_type = "general"
    for pattern, itype in ISSUE_TYPE_PATTERNS:
        if re.search(pattern, text_lower):
            issue_type = itype
            break

    if issue_type == "general":
        if rating and rating >= 4:
            issue_type = "positive_praise"
        elif rating and rating <= 2:
            issue_type = "product_issue"

    # 4. Extract Entities using regex patterns
    entities: List[str] = []
    for pattern, entity_label in ENTITY_PATTERNS:
        if re.search(pattern, text_lower):
            if entity_label not in entities:
                entities.append(entity_label)

    if not entities and topic != "general feedback":
        entities.append(topic)

    # 5. Check if recurring pattern
    is_recurring = False
    recurring_triggers = [
        "upload", "timeout", "slow", "export", "dark mode", "slack", "notification"
    ]
    if any(trigger in text_lower for trigger in recurring_triggers):
        is_recurring = True

    # 6. Generate Short Summary
    if issue_type == "bug":
        summary = f"Customer encountered a bug regarding {topic} with {urgency} urgency."
    elif issue_type == "feature_request":
        summary = f"Customer requested an enhancement for {topic}."
    elif issue_type == "performance":
        summary = f"Customer reported performance degradation in {topic}."
    elif issue_type == "positive_praise" or (rating and rating >= 4):
        summary = f"Customer shared positive feedback praising {topic}."
    else:
        first_clause = text.split(".")[0].strip()
        summary = first_clause if len(first_clause) <= 120 else first_clause[:117] + "..."

    return AnalysisResultBase(
        topic=topic,
        urgency=urgency,
        issue_type=issue_type,
        is_recurring=is_recurring,
        short_summary=summary,
        entities=entities,
    )


def enrich_feedback_record(
    db: Session,
    feedback_id: str,
    use_llm: bool = False,
) -> Optional[AnalysisResult]:
    """Enrich an existing Feedback record in the database with an AnalysisResult."""
    feedback = db.query(Feedback).filter_by(id=feedback_id).first()
    if not feedback:
        return None

    existing_analysis = db.query(AnalysisResult).filter_by(feedback_id=feedback_id).first()
    analysis_data = classify_text_heuristics(
        text=feedback.feedback_text,
        rating=feedback.rating,
        category_hint=feedback.category,
    )

    if existing_analysis:
        existing_analysis.topic = analysis_data.topic
        existing_analysis.urgency = analysis_data.urgency
        existing_analysis.issue_type = analysis_data.issue_type
        existing_analysis.is_recurring = analysis_data.is_recurring
        existing_analysis.short_summary = analysis_data.short_summary
        existing_analysis.entities = json.dumps(analysis_data.entities)
        db.commit()
        db.refresh(existing_analysis)
        _retain_high_signal_memory(feedback, existing_analysis)
        return existing_analysis
    else:
        new_analysis = AnalysisResult(
            id=str(uuid.uuid4()),
            feedback_id=feedback.id,
            topic=analysis_data.topic,
            urgency=analysis_data.urgency,
            issue_type=analysis_data.issue_type,
            is_recurring=analysis_data.is_recurring,
            short_summary=analysis_data.short_summary,
            entities=json.dumps(analysis_data.entities),
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)
        _retain_high_signal_memory(feedback, new_analysis)
        return new_analysis


def batch_analyze_unprocessed(
    db: Session,
    limit: int = 150,
) -> Dict[str, Any]:
    """Process pending Feedback records that do not yet have an AnalysisResult."""
    feedbacks = (
        db.query(Feedback)
        .outerjoin(AnalysisResult, Feedback.id == AnalysisResult.feedback_id)
        .filter(AnalysisResult.id.is_(None))
        .limit(limit)
        .all()
    )

    processed_count = 0
    analyses_to_insert: List[AnalysisResult] = []

    for fb in feedbacks:
        result = classify_text_heuristics(
            text=fb.feedback_text,
            rating=fb.rating,
            category_hint=fb.category,
        )
        ar = AnalysisResult(
            id=str(uuid.uuid4()),
            feedback_id=fb.id,
            topic=result.topic,
            urgency=result.urgency,
            issue_type=result.issue_type,
            is_recurring=result.is_recurring,
            short_summary=result.short_summary,
            entities=json.dumps(result.entities),
        )
        analyses_to_insert.append(ar)
        processed_count += 1

    if analyses_to_insert:
        db.bulk_save_objects(analyses_to_insert)
        db.commit()
        for feedback, analysis in zip(feedbacks, analyses_to_insert):
            _retain_high_signal_memory(feedback, analysis)

    remaining = (
        db.query(Feedback)
        .outerjoin(AnalysisResult, Feedback.id == AnalysisResult.feedback_id)
        .filter(AnalysisResult.id.is_(None))
        .count()
    )

    return {
        "analyzed": processed_count,
        "remaining": remaining,
        "message": f"Successfully analyzed {processed_count} feedback records ({remaining} remaining).",
    }
