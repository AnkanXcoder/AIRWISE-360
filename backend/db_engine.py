
import os
from pathlib import Path
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# Load local environment variables if a .env file exists.
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "airwise.db"

# Read the production/local database configuration.
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # PostgreSQL: use Psycopg 3.
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://",
            "postgresql+psycopg://",
            1
        )
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1
        )

    DATABASE_TYPE = "postgresql"

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True
    )

else:
    # Local development: use the existing SQLite database.
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    DATABASE_TYPE = "sqlite"

    sqlite_url = URL.create(
        drivername="sqlite",
        database=str(DATABASE_PATH)
    )

    engine = create_engine(
        sqlite_url,
        connect_args={"check_same_thread": False}
    )


@contextmanager
def get_connection():
    """Provide a database connection for read operations."""

    with engine.connect() as connection:
        yield connection


@contextmanager
def get_transaction():
    """Provide a connection with automatic transaction handling."""

    with engine.begin() as connection:
        yield connection


def test_connection():
    """Check whether the configured database is reachable."""

    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return result.scalar_one()
