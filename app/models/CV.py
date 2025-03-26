from sqlalchemy import String,Integer,Column
from sqlalchemy.orm import relationship
from app.database import Base

class ResumePDF(Base):
    __tablename__ = "resume_pdfs"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)  # Имя файла
    file_path = Column(String, nullable=False)  # Путь к файлу
