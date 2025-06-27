from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/postgres")

# Create SQLAlchemy engine with write optimization (development settings)
engine = create_engine(
    DATABASE_URL,
    # Connection pool optimizations for development
    pool_size=10,                    # Reduced for local development
    max_overflow=20,                 # Smaller overflow for MacBook
    pool_pre_ping=True,              # Verify connections are alive
    pool_recycle=3600,               # Recycle connections every hour
    
    # Write performance optimizations
    echo=False,                      # Disable query logging in production
)

# Create SessionLocal class with optimized settings
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False,     # Disable auto-flush for better bulk insert performance
    bind=engine
)

# Create Base class for models
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()