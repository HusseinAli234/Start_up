# resume_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.job_seekers import Resume
from app.database import get_db
from app.services.resume_service import ResumeService
from app.schemas.resume_schema import ResumeResponse
from typing import List
from sqlalchemy.orm import selectinload


router = APIRouter(prefix="/resumes", tags=["Resumes"])

@router.get("/", response_model=List[ResumeResponse])
async def get_all_resumes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Resume)
        .options(
            selectinload(Resume.skills),
            selectinload(Resume.educations),
            selectinload(Resume.experiences),
        )
    )
    resumes = result.scalars().all()
    return resumes

@router.get("/{resume_id}", response_model=ResumeResponse)  # Указываем схему ответа
async def get_resume_by_id(resume_id: int, db: AsyncSession = Depends(get_db)):
    service = ResumeService(db)
    resume = await service.get_resume(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume

@router.delete("/{resume_id}")
async def delete_resume(resume_id: int, db: AsyncSession = Depends(get_db)):
    service = ResumeService(db)
    resume = await service.delete_resume(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"message": "Resume deleted successfully"}
