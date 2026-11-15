"""Database engine and session factory."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def init_db():
    from database import models  # noqa: F401 — registers ORM models
    Base.metadata.create_all(bind=engine)


def get_session():
    """Context-manager-friendly session getter."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
