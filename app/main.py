# main.py
import os
from dotenv import load_dotenv
load_dotenv(override=True)
import aiofiles
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine, get_db
from app.models.base import Base
from app.models.employers import JobPosting
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
from starlette.middleware.cors import CORSMiddleware
from app.ai.social_analyzer import analyze_social,analyze_proffesion
from  app.services.cv_services import CVService
from  app.services.vacancy_service import JobPostingService
from app.ai.gisto import generate_pdf_for_single_resume,upload_pdf_to_gcs
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
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from google.cloud import storage # Import GCS client
import io
from urllib.parse import quote


logger = logging.getLogger(__name__)





@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","http://localhost:3001","http://localhost","https://api.sand-box.pp.ua","http://api.sand-box.pp.ua","https://husseinali234.github.io","https://sandbox-front-dev-390134393019.us-central1.run.app","https://sandbox.sdinis.org"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(job_seekers_router.router)
app.include_router(vacancy_router.router)
app.include_router(users_router.router)
app.include_router(test_router.router)


# Remove local upload dir if not needed
# UPLOAD_DIR = "back_media/"
# os.makedirs(UPLOAD_DIR, exist_ok=True)

# Add GCS config (e.g., from env vars or settings)
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "your-default-bucket-name") # Replace with your bucket name


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

async def process_file(file: UploadFile, vacancy_id: int, user: User):
    try:
        credentials_path = "school-kg-7bd58d53b816.json"
        storage_client = storage.Client.from_service_account_json(credentials_path)

        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob_name = f"resumes/{user.id}/{vacancy_id}/{file.filename}"
        blob = bucket.blob(blob_name)

        contents = await file.read()
        await file.seek(0)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, blob.upload_from_string, contents, file.content_type)

        gcs_uri = f"gs://{GCS_BUCKET_NAME}/{blob_name}"

        async with AsyncSessionLocal() as db:
            user = await db.merge(user)
            logger.info(f"🚀 Starting background task for resume {vacancy_id}")
            cv_services = CVService(db)
            service = resume_service.ResumeService(db)
            vacancy_service = JobPostingService(db)
            vacancy = await vacancy_service.get_job_posting(vacancy_id,user)
            file_extension = os.path.splitext(file.filename)[1].lower()
            
            if file_extension == ".pdf":
                parsed_data = await cv_services.parse_pdf(gcs_uri, vacancy_id)
            elif file_extension == ".docx":
                parsed_data = await cv_services.parse_docx(gcs_uri, vacancy_id)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file format: {file.filename}")

            if not parsed_data:
                raise HTTPException(status_code=400, detail=f"Failed to parse file: {file.filename}")

            try:
                resume_data = ResumeCreate(**parsed_data)
            except ValidationError as e:
                raise HTTPException(status_code=400, detail=f"Data validation error in {file.filename}: {e.errors()}")

            db_resume = await service.create_resume(resume_data, vacancy_id=vacancy_id, user=user, gcs_uri=gcs_uri)
            vc_description = db_resume.job_postings[0].description
            vc_title = db_resume.job_postings[0].title
            vc_requirements = db_resume.job_postings[0].requirements
            logger.info(f"🚀 Starting background task for resume {vc_title}")

            asyncio.create_task(background_task(
                db_resume.id, gcs_uri, vc_description, vc_title, vc_requirements, file_extension, db_resume.fullname,vacancy
            ))

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


async def background_task(resume_id: int, gcs_uri: str, description: str, title: str, requirements: str, ext: str, resume_name: str,vacancy:JobPosting):
    try:
        async with AsyncSessionLocal() as db:
            logger.info(f"🚀 Starting background task for resume {resume_id}")
            service = resume_service.ResumeService(db)
            cv_services = CVService(db)
            test_services = TestService(db)

            if ext == ".pdf":
                text = await cv_services.parse_pdf_to_text(gcs_uri)
            elif ext == ".docx":
                text = await cv_services.parse_docx_to_text(gcs_uri)
            else:
                logger.error(f"Unsupported file format in background task for resume {resume_id}")
                return  # Просто выход без падения таски

            profession = await analyze_proffesion(title, description, requirements)
            tests_id = await test_services.get_test_ids_by_proffesion(profession)
            employers_tests = await test_services.get_test_ids_by_proffesion(profession + "(employer)")
            await emailProccess(resume_id, text, tests_id, employers_tests, resume_name,vacancy.user.name,vacancy.title)

            social_skills = await analyze_social(text, title, description, requirements, resume_id)
            await service.resume_skill_add(resume_id, social_skills)

            await db.commit()
    except Exception as e:
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

@app.get("/download_resume/{resume_id}")
async def download_resume(
    resume_id: int,
    user: User = Depends(safe_get_current_subject),
    db: AsyncSession = Depends(get_db)
):
    # Get resume from database
    resume_svc = resume_service.ResumeService(db)
    resume = await resume_svc.get_resume(resume_id, user)
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if not resume.cv_gcs_uri:
        raise HTTPException(status_code=404, detail="PDF file not found for this resume")
    
    try:
        # Initialize GCS client
        credentials_path = "school-kg-7bd58d53b816.json"
        storage_client = storage.Client.from_service_account_json(credentials_path)
        
        # Parse the GCS URI to get bucket name and blob path
        # Format: gs://bucket-name/path/to/file
        uri_parts = resume.cv_gcs_uri.replace("gs://", "").split("/", 1)
        bucket_name = uri_parts[0]
        blob_name = uri_parts[1]
        
        # Get bucket and blob
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Download file content
        content = blob.download_as_bytes()
        
        # Extract original filename from the blob name
        filename = blob_name.split("/")[-1]
        
        # Return streaming response with PDF content
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
            headers={
    "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
}
        )
    except Exception as e:
        logger.error(f"Error downloading resume PDF: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving PDF: {str(e)}")
    
@app.get("/download_analysis/{resume_id}")
async def download_analysis(
    resume_id: int,
    user: User = Depends(safe_get_current_subject),
    db: AsyncSession = Depends(get_db)
):
    try:
        resume_svc = resume_service.ResumeService(db)
        resume = await resume_svc.get_resume(resume_id, user)

        # Генерируем PDF
        pdf_path = await generate_pdf_for_single_resume(resume)

        # Чтение и удаление временного файла
        with open(pdf_path, "rb") as f:
            content = f.read()
        os.remove(pdf_path)

        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=report_resume_{resume_id}.pdf"}
        )

    except Exception as e:
        logger.error(f"Ошибка генерации PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Не удалось создать отчёт.")
