"""
Database connection and session lifecycle management.
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.config.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Ensure directory for SQLite database exists if using relative path
db_url = settings.database_url
if db_url.startswith("sqlite:///./"):
    rel_path = db_url.replace("sqlite:///./", "")
    dir_name = os.path.dirname(rel_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

# For SQLite, enable check_same_thread=False to support Streamlit multithreading
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    """Initialize all database tables and perform lightweight schema migrations."""
    try:
        from app.database import models  # noqa: F401
        from sqlalchemy import text
        Base.metadata.create_all(bind=engine)

        # Lightweight schema migration for existing SQLite databases
        if engine.name == "sqlite":
            with engine.connect() as conn:
                # Check interviews table columns
                existing_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(interviews)")).fetchall()]
                interview_cols_to_add = {
                    "mode": "VARCHAR(50) DEFAULT 'TEXT'",
                    "estimated_duration_minutes": "INTEGER DEFAULT 30",
                    "language": "VARCHAR(50) DEFAULT 'English'",
                    "interviewer_persona": "VARCHAR(100)",
                    "topics_json": "TEXT",
                    "config_json": "TEXT",
                }
                for col_name, col_type in interview_cols_to_add.items():
                    if col_name not in existing_cols:
                        conn.execute(text(f"ALTER TABLE interviews ADD COLUMN {col_name} {col_type}"))

                # Check questions table columns
                existing_q_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(questions)")).fetchall()]
                q_cols_to_add = {
                    "topic": "VARCHAR(100) DEFAULT 'General'",
                    "question_type": "VARCHAR(50) DEFAULT 'Technical'",
                    "expected_concepts_json": "TEXT",
                    "evaluation_criteria_json": "TEXT",
                    "follow_up_possible": "INTEGER DEFAULT 1",
                    "metadata_json": "TEXT",
                }
                for col_name, col_type in q_cols_to_add.items():
                    if col_name not in existing_q_cols:
                        conn.execute(text(f"ALTER TABLE questions ADD COLUMN {col_name} {col_type}"))

                # Check evaluations table columns
                existing_ev_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(evaluations)")).fetchall()]
                ev_cols_to_add = {
                    "criteria_scores_json": "TEXT",
                    "evidence_json": "TEXT",
                    "assessment_disclaimer": "TEXT",
                }
                for col_name, col_type in ev_cols_to_add.items():
                    if col_name not in existing_ev_cols:
                        conn.execute(text(f"ALTER TABLE evaluations ADD COLUMN {col_name} {col_type}"))
                conn.commit()

        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager for obtaining a database session."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
