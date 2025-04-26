import asyncio
import pdfplumber
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from docx import Document
from app.models.employers import JobPosting
from app.schemas.vacancy_schema import SkillSchema
from app.ai.analyzer import analyze_resume,analyze_resume_chatgpt


class CVService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _read_pdf(self, file_path: str) -> str:
        text = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(layout=True)
                if page_text:
                    text.append(page_text)           
        return "\n".join(text)
    
    def _read_docx(self, file_path: str) -> str:
        doc = Document(file_path)
        full_text = []

        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text.strip())

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        full_text.append(cell.text.strip())

        return "\n".join(full_text)
    


    async def parse_pdf_to_text(self, file_path: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._read_pdf, file_path)
    
    async def parse_docx_to_text(self, file_path: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._read_docx, file_path)
    


    async def parse_docx(self, file_path: str, vacancy_id: int) -> dict:
        if vacancy_id is None:
            raise HTTPException(status_code=400, detail="vacancy_id is required")

        text = await self.parse_docx_to_text(file_path)

        stmt = (
            select(JobPosting)
            .where(JobPosting.id == vacancy_id)
            .options(selectinload(JobPosting.skills))
        )
        result = await self.db.execute(stmt)
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(status_code=404, detail="Vacancy not found")

        skills = [SkillSchema(title=skill.title) for skill in job.skills]
        requirements = job.requirements

        return await analyze_resume(text, skills, requirements)

    async def parse_pdf(self, file_path: str, vacancy_id: int) -> dict:
        if vacancy_id is None:
            raise HTTPException(status_code=400, detail="vacancy_id is required")

        text = await self.parse_pdf_to_text(file_path)

        stmt = (
            select(JobPosting)
            .where(JobPosting.id == vacancy_id)
            .options(selectinload(JobPosting.skills))
        )
        result = await self.db.execute(stmt)
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(status_code=404, detail="Vacancy not found")

        skills = [SkillSchema(title=skill.title) for skill in job.skills]
        requirements = job.requirements

        return await analyze_resume(text, skills, requirements)
