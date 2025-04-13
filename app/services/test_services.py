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
        )
        db_test.questions = [
            TestQuestion(question=ques.question, mark=ques.mark)
            for ques in test_create.questions
        ]
        with self.db.no_autoflush:    
            self.db.add(db_test)
        await self.db.commit()
        await self.db.refresh(db_test)
        return db_test  
    



    async def get_test(self, test_id: int) -> JobPosting:
        result = await self.db.execute(
            select(SocialTest)
            .filter_by(id=test_id)
            .options(
                selectinload(SocialTest.questions),
            )
        )
        return result.scalars().first()
    async def delete_test(self, test_id: int, user: User) -> bool:
        test = await self.get_test(test_id, user)
        if not test:
            return False
        await self.db.delete(test)
        await self.db.commit()
        return True    