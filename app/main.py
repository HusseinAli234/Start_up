from fastapi import FastAPI,File,UploadFile
from app.routers import users
from app.database import Base, engine
from fastapi.responses import FileResponse
from app.services import cv_services
from app.services import resume_service
from fastapi import Depends
from app.database import get_db 
from sqlalchemy.orm import Session
import shutil
import os
app = FastAPI()
app.include_router(users.router)
Base.metadata.create_all(bind=engine)
UPLOAD_DIR = "uploads" 
os.makedirs(UPLOAD_DIR, exist_ok=True) 
@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files are accepted"}

    file_path = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    parsed_data = cv_services.parse_pdf(file_path)
    resume_data = resume_service.ResumeCreate(**parsed_data)

    resume_service_instance = resume_service.ResumeService(db) 
    db_resume = resume_service_instance.create_resume(resume_data)  

    return db_resume 

