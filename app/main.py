# main.py
import os
import aiofiles
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine, get_db
from app.models.base import Base
from app.schemas.resume_schema import ResumeCreate
from app.services import cv_services, resume_service,vacancy_service
from contextlib import asynccontextmanager
from pydantic import ValidationError
from app.routers import job_seekers as job_seekers_router
from app.routers import vacancy as vacancy_router
from typing import Optional
from fastapi import Query
from app.schemas.vacancy_schema import VacancyCreate
from fastapi.middleware.cors import CORSMiddleware
from app.ai.social_analyzer import analyze_social
from concurrent.futures import ThreadPoolExecutor
import asyncio
from .users import views as users_router
from .users.config import safe_get_current_subject
from .users.models import User

executor = ThreadPoolExecutor()

async def run_in_thread(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(job_seekers_router.router)
app.include_router(vacancy_router.router)
app.include_router(users_router.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешает все домены (замените на список доменов для ограничения)
    allow_credentials=True,
    allow_methods=["*"],  # Разрешает все методы (GET, POST, PUT и т. д.)
    allow_headers=["*"],  # Разрешает все заголовки
)


UPLOAD_DIR = "back_media/"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...), db: AsyncSession = Depends(get_db),
                     user: User = Depends(safe_get_current_subject), vacancy_id: Optional[int] = Query(default=None)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    async with aiofiles.open(file_path, "wb") as out_file:
        while chunk := await file.read(1024 * 1024):  # Читаем по 1MB
            await out_file.write(chunk)


    # Парсинг PDF-файла (ожидается, что функция вернет dict, соответствующий ResumeCreate)
    parsed_data = cv_services.parse_pdf(file_path)
    if not parsed_data:
        raise HTTPException(status_code=400, detail="Failed to parse PDF")


    
    try:
        resume_data = ResumeCreate(**parsed_data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Data validation error: {e.errors()}")
    service = resume_service.ResumeService(db)
    db_resume = await service.create_resume(resume_data, vacancy_id=vacancy_id, user=user)
    async def background_task():
        text = cv_services.parse_pdf_to_text(file_path)
        social_skills = await run_in_thread(analyze_social, text)
        await service.resume_skill_add(db_resume.id, social_skills)
    asyncio.create_task(background_task()) 
    return JSONResponse(content={"id": db_resume.id, "fullname": db_resume.fullname, "location": db_resume.location})



@app.post("/vacancy_post")
async def upload_vacancy(vacancy: VacancyCreate, db: AsyncSession = Depends(get_db), user: User = Depends(safe_get_current_subject)):
    service = vacancy_service.JobPostingService(db)
    db_vacancy = await service.create_job_posting(vacancy, user)
    return JSONResponse(content={"id": db_vacancy.id, "title": db_vacancy.title, "location": db_vacancy.location})
