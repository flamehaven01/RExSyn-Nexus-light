from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.settings import settings
from typing import Generator
from sqlalchemy.orm import Session

engine = create_engine(settings.DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
