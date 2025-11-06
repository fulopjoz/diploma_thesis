"""
SQLAlchemy database session management.

This module handles database engine creation and session management.
Falls back to SQLite for testing when DATABASE_URL is not set.
"""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# If no DATABASE_URL is set, use SQLite for testing
if DATABASE_URL is None:
    DATABASE_URL = "sqlite:///./test_classifier.db"
    # SQLite-specific configuration
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL or other database
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
