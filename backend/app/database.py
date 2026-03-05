import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "oscar.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    from app.models import Policy, Download, StructuredPolicy  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized at %s", DB_PATH)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
