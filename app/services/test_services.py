from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.job_seekers import Resume, Education, Experience, Skill, TypeSkill,HardTotal,SocialTest,TestQuestion
from app.schemas.resume_schema import ResumeCreate
from app.schemas.test_schema import CreateTest
from sqlalchemy.orm import selectinload
from sqlalchemy import delete
from app.models.employers import JobPosting
from fastapi import FastAPI, HTTPException
from app.users.models import User
from fastapi import status


app = FastAPI()


class TestService:
    def __init__(self, db: AsyncSession):
        self.db = db


    async def add_test(self,test_create:CreateTest,user: User)-> SocialTest:
        db_test = SocialTest(
            title=test_create.title,
            user_id=user.id,
            proffesion=test_create.proffesion,
            is_Optional=test_create.isOptional,
        )
        db_test.questions = [
            TestQuestion(question=ques.question, mark=ques.mark,source=ques.source)
            for ques in test_create.questions
        ]
        with self.db.no_autoflush:    
            self.db.add(db_test)
        await self.db.commit()
        await self.db.refresh(db_test)
        return db_test  
    

    async def get_test_ids_by_proffesion(self, find_proffesion: str) -> list[int]:
        result = await self.db.execute(
            select(SocialTest.id).where(SocialTest.proffesion == find_proffesion)
        )
        return result.scalars().all()


    async def get_test(self, test_id: int) -> SocialTest:
        result = await self.db.execute(
            select(SocialTest)
            .filter_by(id=test_id)
            .options(
                selectinload(SocialTest.questions),
            )
        )
        return result.scalars().first()
    
    async def delete_test(self, test_id: int) -> bool:
        test = await self.get_test(test_id)
        if not test:
            return False
        await self.db.delete(test)
        await self.db.commit()
        return True    