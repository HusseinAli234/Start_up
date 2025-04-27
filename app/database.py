import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv() # Load .env for local development

# --- Database Configuration ---
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME") # e.g., your-project:us-central1:your-instance

# Determine if running in Cloud Run (or similar serverless environment)
# K_SERVICE is automatically set by Cloud Run.
# You could use a different custom env var if preferred.
IS_CLOUD_RUN = os.getenv("K_SERVICE")

# Ensure required variables are set
if not DB_USER or not DB_PASSWORD or not DB_NAME:
    raise ValueError("DB_USER, DB_PASSWORD, and DB_NAME environment variables must be set")
if IS_CLOUD_RUN and not INSTANCE_CONNECTION_NAME:
     raise ValueError("INSTANCE_CONNECTION_NAME must be set when running in Cloud Run")

# Construct the DATABASE_URL
if IS_CLOUD_RUN:
    # Cloud SQL Unix socket path
    # The /cloudsql/ prefix is standard for Cloud Run SQL connections
    # The .s.PGSQL.5432 suffix is specific to PostgreSQL
    unix_socket_path = f"/cloudsql/{INSTANCE_CONNECTION_NAME}/.s.PGSQL.5432"
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?host={unix_socket_path}"
else:
    # Local development/testing (using Cloud SQL Proxy)
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1") # Proxy listens on localhost
    DB_PORT = os.getenv("DB_PORT", "5432")     # The port you told the proxy to use
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"Connecting to DB: {'Cloud Run Socket' if IS_CLOUD_RUN else DATABASE_URL.split('@')[-1]}") # Log connection type

# --- SQLAlchemy Setup ---
engine = create_async_engine(
    DATABASE_URL,
    echo=False, # Set echo=True for debugging SQL
    # Add pool settings recommended for Cloud SQL / Serverless
    pool_size=5,           # Start with a small pool size
    max_overflow=2,        # Limit overflow connections
    pool_timeout=30,       # Wait time for connection from pool
    pool_recycle=1800      # Recycle connections periodically (e.g., 30 mins)
)

# Factory for creating sessions
AsyncSessionLocal = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

# --- Dependency for FastAPI ---
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Implicit commit handled by context manager if no error
        except Exception:
            await session.rollback() # Explicit rollback on any exception
            raise # Re-raise the exception
        finally:
            # Session closed automatically by 'async with'
            pass

# async def get_db():
#     async with AsyncSessionLocal() as session:
#         try:
#             yield session
#         finally:
#             await session.close()