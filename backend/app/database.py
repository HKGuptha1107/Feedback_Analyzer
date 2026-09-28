"""Database connection, session management, and Base model definition.
Supports dual-mode: SQLite (zero-config local) & PostgreSQL (production / Docker).
"""

from typing import Generator
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

# Engine configuration
connect_args = {}
if settings.is_sqlite:
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    future=True,
)

# Enable foreign key enforcement for SQLite
if settings.is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

# Base class for SQLAlchemy ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding database sessions per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all database tables defined in models."""
    import app.models  # noqa: F401 - ensure models are registered
    Base.metadata.create_all(bind=engine)
    if "feedbacks" in inspect(engine).get_table_names():
        columns = {column["name"] for column in inspect(engine).get_columns("feedbacks")}
        if "conversation_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE feedbacks ADD COLUMN conversation_id VARCHAR(64)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_feedback_conversation ON feedbacks (conversation_id, feedback_date)"))
