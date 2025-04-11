# main.py
import os
import aiofiles
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine, get_db
from app.models import Base
from app.schemas.resume_schema import ResumeCreate
from app.services import resume_service,vacancy_service
from contextlib import asynccontextmanager
from pydantic import ValidationError
from app.routers import job_seekers as job_seekers_router
from app.routers import vacancy as vacancy_router
from typing import Optional
from fastapi import Query
from app.schemas.vacancy_schema import VacancyCreate
from fastapi.middleware.cors import CORSMiddleware
from app.ai.social_analyzer import analyze_social
from  app.services.cv_services import CVService
import asyncio
from typing import List
from app.database import AsyncSessionLocal
import logging
logging.basicConfig()    
logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(job_seekers_router.router)
app.include_router(vacancy_router.router)

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
async def upload_pdf(
    files: List[UploadFile] = File(...),
    vacancy_id: Optional[int] = Query(default=None)
):
    if vacancy_id is None:
        raise HTTPException(status_code=400, detail="vacancy_id is required")
    # Запуск всех задач параллельно
    tasks = [process_file(file,vacancy_id) for file in files]
    results = await asyncio.gather(*tasks)
    return JSONResponse(content={"resumes": results})

async def process_file(file: UploadFile,vacancy_id:int):
    try:    
        async with AsyncSessionLocal() as db:
            cv_services = CVService(db)
            service = resume_service.ResumeService(db)
            if not file.filename.endswith(".pdf"):
                raise HTTPException(status_code=400, detail=f"File {file.filename} is not a valid PDF")

            file_path = os.path.join(UPLOAD_DIR, file.filename)

            async with aiofiles.open(file_path, "wb") as out_file:
                while chunk := await file.read(1024 * 1024):
                    await out_file.write(chunk)

            parsed_data = await cv_services.parse_pdf(file_path, vacancy_id)
            if not parsed_data:
                raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {file.filename}")

            try:
                resume_data = ResumeCreate(**parsed_data)
            except ValidationError as e:
                raise HTTPException(status_code=400, detail=f"Data validation error in {file.filename}: {e.errors()}")

            db_resume = await service.create_resume(resume_data, vacancy_id=vacancy_id)
            
            asyncio.create_task(background_task(db_resume.id,file_path))
            

            return {
                    "id": db_resume.id,
                    "fullname": db_resume.fullname,
                    "location": db_resume.location
                }
    except Exception as e:
        # Логирование ошибки или дополнительные действия
        print(f"Error in file task for resume: {e}")    

async def background_task(resume_id: int, file_path: str):
    try:
        async with AsyncSessionLocal() as db:
            service = resume_service.ResumeService(db)
            cv_services = CVService(db)
            text = await cv_services.parse_pdf_to_text(file_path)
            social_skills = await analyze_social(text)
            await service.resume_skill_add(resume_id, social_skills)
            await db.commit()
    except Exception as e:
        # Логирование ошибки или дополнительные действия
        print(f"Error in background task for resume {resume_id}: {e}")


@app.post("/vacancy_post")
async def upload_vacancy(vacancy: VacancyCreate ,db:AsyncSession = Depends(get_db)):
    service =  vacancy_service.JobPostingService(db)
    db_vacancy = await service.create_job_posting(vacancy)
    return JSONResponse(content={"id": db_vacancy.id, "title": db_vacancy.title, "location": db_vacancy.location})
