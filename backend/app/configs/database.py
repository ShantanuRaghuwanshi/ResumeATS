from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Example: Replace with your actual database URL
SQLALCHEMY_DATABASE_URL = (
    "sqlite:///./test.db"  # For SQLite; use proper URL for PostgreSQL/MySQL
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
