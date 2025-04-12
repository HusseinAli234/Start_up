import re
import difflib
from statistics import mean
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.users.models import User
from app.models.employers import VacancySkill, JobPosting  
from app.schemas.vacancy_schema import VacancyCreate
from app.models.job_seekers import Resume

def normalize(skill: str) -> str:
    """
    Приводит строку к нижнему регистру и удаляет все цифры.
    Например: "Django 5" -> "django"
    """
    return re.sub(r'\d+', '', skill).strip().lower()

def skills_match(skill_a: str, skill_b: str, threshold: float = 0.8) -> bool:
    """
    Возвращает True, если навыки считаются совпадающими.
    Сначала выполняется проверка вхождения одного нормализованного навыка в другой,
    если не сработало, используется коэффициент схожести.
    """
    norm_a = normalize(skill_a)
    norm_b = normalize(skill_b)
    
    # Проверка наличия подстроки
    if norm_a in norm_b or norm_b in norm_a:
        return True
    
    # Вычисление коэффициента схожести
    similarity_ratio = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()
    return similarity_ratio >= threshold

class JobPostingService:
    def __init__(self, db: AsyncSession):
        self.db = db    

    async def create_job_posting(self, job_data: VacancyCreate, user: User) -> JobPosting:
        db_job = JobPosting(
            title=job_data.title,
            location=job_data.location,
            description=job_data.description,
            salary=job_data.salary,
            user_id=user.id,
            requirements = job_data.requirements,
            skills=[
                VacancySkill(
                    title=skill.title,
                )
                for skill in job_data.skills
            ]
        )
        self.db.add(db_job)
        await self.db.commit()
        await self.db.refresh(db_job)
        return db_job

    async def get_job_posting(self, job_id: int, user: User) -> JobPosting:
        result = await self.db.execute(
            select(JobPosting)
            .filter_by(id=job_id, user_id=user.id)
            .options(
                selectinload(JobPosting.skills),
                selectinload(JobPosting.resumes)
            )
        )
        return result.scalars().first()
        
    async def sort_by_hard(self, job_id: int, user: User = None):
        result = await self.db.execute(
            select(JobPosting)
            .filter_by(id=job_id, user_id=user.id)
            .options(
                selectinload(JobPosting.skills),
                selectinload(JobPosting.resumes).selectinload(Resume.skills)
            )
            .where(JobPosting.id == job_id)
        )

        job_posting = result.scalars().first()
        if not job_posting:
            return []

        # Вывод информации по вакансии
        print(f"Оцениваем вакансию: {job_posting.title}")
        vacancy_skills = [(skill.title, normalize(skill.title)) for skill in job_posting.skills]
        print("Навыки вакансии (оригинальный и нормализованный вид):", vacancy_skills)

        resume_scores = []

        for resume in job_posting.resumes:
            matched_levels = []
            print(f"\nОцениваем резюме: {resume.fullname}")
            for r_skill in resume.skills:
                r_skill_norm = normalize(r_skill.title)
                matches = []
                # Для каждого навыка резюме пробуем найти совпадения с навыками вакансии
                for v_skill in job_posting.skills:
                    is_match = skills_match(r_skill.title, v_skill.title)
                    v_skill_norm = normalize(v_skill.title)
                    matches.append((v_skill.title, is_match))
                    if is_match:
                        # Делим значение на 10, чтобы перевести оценку с 100-бальной шкалы на 10-бальную
                        matched_levels.append(r_skill.level)
                print(f"Навык резюме: '{r_skill.title}' (нормализовано: '{r_skill_norm}') -> Совпадения: {matches}")
            avg_score = mean(matched_levels) if matched_levels else 0
            print(matched_levels)
            
            print(f"Средний балл для {resume.fullname}: {avg_score}")
            resume_scores.append((resume, avg_score))

        # Сортировка резюме по убыванию среднего балла
        sorted_resumes = sorted(resume_scores, key=lambda item: item[1], reverse=True)
        print("\nОтсортированные резюме:")
        for r, score in sorted_resumes:
            print(f"{r.fullname} - Средний балл: {score}")

        return [{"resume": r.fullname, "avg_skill_score": score} for r, score in sorted_resumes]
    
    async def delete_job_posting(self, job_id: int, user: User) -> bool:
        job = await self.get_job_posting(job_id, user)
        if not job:
            return False
        await self.db.delete(job)
        await self.db.commit()
        return True
