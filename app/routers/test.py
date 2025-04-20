from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.job_seekers import SocialTest
from app.database import get_db
from app.services.test_services import TestService
from app.schemas.test_schema import ResponseTest,ResultOfTest
from typing import List
from sqlalchemy.orm import selectinload
from app.users.config import security, config, safe_get_current_subject
from app.users.models import User



router = APIRouter(prefix="/test", tags=["Test"])
@router.get("/", response_model=List[ResponseTest])
async def get_all_test(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SocialTest)
        .options(
            selectinload(SocialTest.questions),
        )
    )
    tests = result.scalars().all()
    return tests

@router.get("/{test_id}", response_model=ResponseTest)
async def get_test_by_id(test_id: int, db: AsyncSession = Depends(get_db)):
    service = TestService(db)
    test = await service.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Тест не найдена или у вас нет доступа к ней")
    return test

@router.delete("/{test_id}")
async def delete_vacancy(test_id: int, db: AsyncSession = Depends(get_db)):
    service = TestService(db)
    if not await service.delete_test(test_id):  # Передаем user сюда
        raise HTTPException(status_code=404, detail="Test not found or you don't have permission to delete it")
    
    return {"message": "Test deleted successfully"}

    