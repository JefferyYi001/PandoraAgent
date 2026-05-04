"""
SQLite connection management - single instance with WAL mode
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from config.settings import get_settings
from utils.logger import logger

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
            echo=False,
        )
        # Enable WAL mode for better concurrent access
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
            logger.info("SQLite WAL mode enabled")
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def get_session() -> Session:
    """Get a new database session (caller must close it)"""
    return get_session_factory()()


def init_db():
    """Create all tables"""
    from db.models import Base
    Base.metadata.create_all(bind=get_engine())
    logger.info("Database initialized")
