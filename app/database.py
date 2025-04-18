import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from contextlib import asynccontextmanager
load_dotenv()
# Использование переменной окружения DATABASE_URL
DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Создаем асинхронный движок
engine = create_async_engine(DATABASE_URL, echo=False)

# Фабрика для создания сессий
AsyncSessionLocal = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# async def get_db():
#     async with AsyncSessionLocal() as session:
#         try:
#             yield session
#         finally:
#             await session.close()