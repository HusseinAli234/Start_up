from sqlalchemy.ext.asyncio import AsyncSession


class PromptService:
    def __init__(self, db: AsyncSession):
        self.db = db
