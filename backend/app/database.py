from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os
import logging

from app.core.config import settings

logger = logging.getLogger("pod_database")

from sqlalchemy.pool import StaticPool

DATABASE_URL = settings.DATABASE_URL
if os.getenv("USE_SQLITE", "false").lower() == "true":
    DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
else:
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as conn:
            pass
    except Exception as e:
        logger.warning(f"Could not connect to PostgreSQL via {DATABASE_URL}: {e}. Falling back to SQLite in-memory database.")
        DATABASE_URL = "sqlite:///:memory:"
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

