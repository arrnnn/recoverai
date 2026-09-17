"""
RecoverAI - Database Connection Test
======================================
Quick sanity check that DATABASE_URL in .env is correct and reachable.
Prints the Postgres version on success. Does not create or modify anything.

Usage:
    python backend/test_db_connection.py
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL is not set in your .env file.")
    sys.exit(1)

print(f"Connecting to database... (host hidden for safety)")

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.scalar()
        print("\n✅ Connection successful!")
        print(f"Postgres version: {version}")
except Exception as e:
    print("\n❌ Connection FAILED.")
    print(f"Error: {e}")
    sys.exit(1)
    