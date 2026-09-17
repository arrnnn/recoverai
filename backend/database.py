"""
RecoverAI - Database Setup
============================
SQLAlchemy engine + session factory, shared across the backend, the
agent's persistence layer, and Alembic migrations.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Add it to your .env file.")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI-style dependency generator (used again in Phase 8)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()