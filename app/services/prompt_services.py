from sqlalchemy.ext.asyncio import AsyncSession
from app.models.promtps import Prompt 

class PromptService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # async def create_prompt(self, prompt: PromptCreate, user: User) -> Prompt:

