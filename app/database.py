import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv


load_dotenv()


PROD = os.getenv("PROD") == "True" 


if PROD:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@postgres_db:5432/postgres_db")
else:
    DATABASE_URL = "sqlite+aiosqlite:///./test.db"


engine = create_async_engine(DATABASE_URL, echo=True)


AsyncSessionLocal = sessionmaker(
    engine, expire_on_commit=True, class_=AsyncSession
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
