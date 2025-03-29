# main.py
import os
import aiofiles
import shutil
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine, get_db, Base
from app.schemas.resume_schema import ResumeCreate
from app.services import cv_services, resume_service
from contextlib import asynccontextmanager
from pydantic import ValidationError
from app.routers import job_seekers as job_seekers_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(job_seekers_router.router)


UPLOAD_DIR = "back_media/"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
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
    db_resume = await service.create_resume(resume_data)
    
    return JSONResponse(content={"id": db_resume.id, "fullname": db_resume.fullname, "location": db_resume.location})
