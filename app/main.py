# main.py
import os
import aiofiles
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine, get_db
from app.models.base import Base
from app.schemas.resume_schema import ResumeCreate
from app.schemas.test_schema import CreateTest
from app.services import resume_service,vacancy_service,test_services
from contextlib import asynccontextmanager
from pydantic import ValidationError
from app.routers import job_seekers as job_seekers_router
from app.routers import vacancy as vacancy_router
from typing import Optional
from fastapi import Query
from app.schemas.vacancy_schema import VacancyCreate
from fastapi.middleware.cors import CORSMiddleware
from app.ai.social_analyzer import analyze_social,analyze_proffesion
from  app.services.cv_services import CVService
import asyncio
from .users import views as users_router
from app.routers import test as test_router
from .users.config import safe_get_current_subject
from .users.models import User
from typing import List
from app.database import AsyncSessionLocal
import logging
from app.schemas.test_schema import ResultOfTest
from app.ai.sms_sendler import emailProccess
from app.services.test_services import TestService

logger = logging.getLogger(__name__)





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
app.include_router(test_router.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000"],  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)
UPLOAD_DIR = "back_media/"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/upload_pdf")
async def upload_pdf(
    files: List[UploadFile] = File(...),
    user: User = Depends(safe_get_current_subject),
    vacancy_id: Optional[int] = Query(default=None)
    ):
    if vacancy_id is None:
        raise HTTPException(status_code=400, detail="vacancy_id is required")
    # Запуск всех задач параллельно
    tasks = [process_file(file, vacancy_id, user) for file in files]
    results = await asyncio.gather(*tasks)
    return JSONResponse(content={"resumes": results})

async def process_file(file: UploadFile, vacancy_id:int, user: User):
    try:    
        async with AsyncSessionLocal() as db:
            user = await db.merge(user)
            logger.info(f"🚀 Starting background task for resume {vacancy_id}")
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

            db_resume = await service.create_resume(resume_data, vacancy_id=vacancy_id, user=user)
            vc_description = db_resume.job_postings[0].description
            vc_title = db_resume.job_postings[0].title
            vc_requirements = db_resume.job_postings[0].requirements
            logger.info(f"🚀 Starting background task for resume {vc_title}")
            asyncio.create_task(background_task(db_resume.id,file_path,vc_description,vc_title,vc_requirements))
            

            return {
                    "id": db_resume.id,
                    "fullname": db_resume.fullname,
                    "location": db_resume.location
                }
    except Exception as e:
        logger.error(f"Error in file task for resume: {e}", exc_info=True)
        return {
            "filename": file.filename,
            "error": str(e)
        }

async def background_task(resume_id: int, file_path: str, description: str, title: str, requirements: str ):
    try:
        async with AsyncSessionLocal() as db:
            logger.info(f"🚀 Starting background task for resume {resume_id}")
            service = resume_service.ResumeService(db)
            cv_services = CVService(db)
            test_services = TestService(db)
            text = await cv_services.parse_pdf_to_text(file_path)
            social_skills = await analyze_social(text,title,description,requirements,resume_id)
            profession = await analyze_proffesion(title,description,requirements)
            tests_id = await test_services.get_test_ids_by_proffesion(profession)
            await emailProccess(resume_id,text,tests_id)
            await service.resume_skill_add(resume_id, social_skills)
            await db.commit()
    except Exception as e:
        # Логирование ошибки или дополнительные действия
        logger.error(f"💥 Error in background task for resume {resume_id}: {e}", exc_info=True)


@app.post("/vacancy_post")
async def upload_vacancy(vacancy: VacancyCreate, db: AsyncSession = Depends(get_db), user: User = Depends(safe_get_current_subject)):
    service = vacancy_service.JobPostingService(db)
    db_vacancy = await service.create_job_posting(vacancy, user)
    return JSONResponse(content={"id": db_vacancy.id, "title": db_vacancy.title, "location": db_vacancy.location})

@app.post("/test_post")
async def upload_test(test: CreateTest, db: AsyncSession = Depends(get_db), user: User = Depends(safe_get_current_subject)):
    service = test_services.TestService(db)
    db_test = await service.add_test(test, user)
    return JSONResponse(content={"id": db_test.id, "title": db_test.title, "proffesion": db_test.proffesion})

@app.post("/result")
async def resultOfTest(result:ResultOfTest,db: AsyncSession = Depends(get_db)):
    service = resume_service.ResumeService(db)
    db_test = await service.test_skill_add(result.resume_id,result.sub_tests)
    return JSONResponse(content={"result": "Success"})
