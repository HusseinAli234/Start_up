from fastapi import FastAPI,File,UploadFile
from app.routers import users
from app.database import Base, engine
from fastapi.responses import FileResponse
from app.services import cv_services
import shutil
import os
app = FastAPI()
app.include_router(users.router)
Base.metadata.create_all(bind=engine)
UPLOAD_DIR = "uploads" 
os.makedirs(UPLOAD_DIR, exist_ok=True) 
@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        return {"error:only Pdf accept"}
    file_path = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_path,"wb") as buffer:
        shutil.copyfileobj(file.file,buffer)
    return  cv_services.parse_pdf(file_path)