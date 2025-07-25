from sqlalchemy.orm import Session
from app.db.base import SessionLocal


def get_db() -> Session:
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
