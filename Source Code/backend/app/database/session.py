import os
import pathlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SCRIPT_DIR = pathlib.Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
DB_DIR = BACKEND_DIR / "database"
DB_DIR.mkdir(parents=True, exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_DIR / 'history_v2.db'}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
