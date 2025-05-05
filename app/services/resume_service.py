import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.job_seekers import Resume, Education, Experience, Skill, TypeSkill,HardTotal,TestTotal,FeedbackTotal
from app.schemas.resume_schema import ResumeCreate
from app.schemas.test_schema import CreateTest
from sqlalchemy.orm import selectinload
from sqlalchemy import delete
from app.services.cv_services import CVService
from app.models.employers import JobPosting
from fastapi import FastAPI, HTTPException
from app.users.models import User
from fastapi import status
from google.cloud.exceptions import NotFound
import logging 
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)


app = FastAPI()
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "your-default-bucket-name")


class ResumeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_resume(self, resume_data: ResumeCreate, user: User, vacancy_id: int | None = None, gcs_uri: str = None) -> Resume:
        db_resume = Resume(
            fullname=resume_data.fullname,
            location=resume_data.location,
            cv_gcs_uri=gcs_uri or resume_data.cv_gcs_uri,  # Use provided GCS URI or from schema
        )

        if resume_data.hard_total:
            db_hard_total = HardTotal(
                total=resume_data.hard_total.total,
                justification=resume_data.hard_total.justification,
                resume=db_resume
            )
            db_resume.hard_total = db_hard_total

        db_resume.experiences = [
            Experience(name=exp.name, description=exp.description, resume=db_resume)
            for exp in resume_data.experience
        ]
        db_resume.educations = [
            Education(name=edu.name, description=edu.description, resume=db_resume)
            for edu in resume_data.education
        ]
        db_resume.skills = [
            Skill(
                title=skill.title,
                level=skill.level,
                justification=skill.justification,
                type=TypeSkill(skill.type),
                resume=db_resume
            )
            for skill in resume_data.skills
        ]
        
        db_resume.user = user

        with self.db.no_autoflush:
            self.db.add(db_resume)
            if resume_data.hard_total:
                self.db.add(db_resume.hard_total)
            self.db.add_all(db_resume.experiences)
            self.db.add_all(db_resume.educations)
            self.db.add_all(db_resume.skills)
            # Удаляем строку self.db.add(db_resume.user)

        if vacancy_id:
            job = await self.db.get(JobPosting, vacancy_id)
            if not job:
                raise HTTPException(status_code=404, detail="Вакансия не найдена")
            if job.user_id != user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="У вас нет прав для прикрепления этой вакансии")
            db_resume.job_postings.append(job)

        self.db.add(db_resume)
        await self.db.commit()
        await self.db.refresh(db_resume)
        return db_resume


    async def resume_skill_add(self, resume_id: int, soft_skills: dict):
        # Проверка на существование резюме
        result = await self.db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()

        if resume is None:
            raise ValueError(f"Resume with id {resume_id} not found")

        # Обновляем soft_total или создаём, если его ещё нет
        soft_total_data = soft_skills.get("soft_total")
        if soft_total_data:
            if resume.soft_total:
                resume.soft_total.total = soft_total_data["total"]
                resume.soft_total.justification = soft_total_data["justification"]
            else:
                from app.models.job_seekers import SoftTotal  # импорт тут, если нет глобального
                resume.soft_total = SoftTotal(
                    total=soft_total_data["total"],
                    justification=soft_total_data["justification"],
                    resume_id=resume_id
                )
        else:
            raise ValueError(f"Problem with social network analyzer!")        



        # Получаем список новых soft-skills
        skills_to_add_data = soft_skills.get("skills", [])

        skills = []
        for skill in skills_to_add_data:
            skill_obj = Skill(
                title=skill["title"],
                level=skill["level"],
                justification=skill["justification"],
                type=TypeSkill.SOFT,
                resume_id=resume_id
            )
            skills.append(skill_obj)

        # Добавляем в сессию
        self.db.add_all(skills)
        await self.db.commit()

    async def test_skill_add(self, resume_id: int, test_skills: list):
        result = await self.db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()

        if resume is None:
            raise ValueError(f"Resume with id {resume_id} not found")

        skills_to_add_data = test_skills
        skills = []

        # Для TEST
        test_summary = 0
        test_max = 0
        has_test = False
        title_name = []

        # Для FEEDBACK
        feedback_summary = 0
        feedback_max = 0
        has_feedback = False

        for skill in skills_to_add_data:
            if skill.is_Optional:  # Отзыв работодателя (feedback)
                has_feedback = True
                if skill.maximum == 0 and skill.result == 0:
                    level = -1
                    justification = "Так охарактеризовал вас бывший работодатель"
                else:
                    level = round((skill.result / skill.maximum) * 100, 2)
                    justification = "Отзыв работодателя"
                    feedback_summary += skill.result
                    feedback_max += skill.maximum

                skills.append(Skill(
                    title=skill.title,
                    level=level,
                    justification=justification,
                    type=TypeSkill.FEEDBACK,
                    resume_id=resume_id
                ))

            else:  # Результаты теста
                has_test = True
                score = round((skill.result / skill.maximum) * 100, 2)
                test_summary += skill.result
                test_max += skill.maximum
                title_name.append(skill.title) 
                skills.append(Skill(
                    title=skill.title,
                    level=score,
                    justification="Результат Опросника",
                    type=TypeSkill.TEST,
                    resume_id=resume_id
                ))

        # Обновляем или создаём TestTotal
        if has_test and test_max > 0:
            new_total = round((test_summary / test_max) * 100, 2)
            
            # Собираем новые уникальные названия
            new_titles = set(title_name)
            
            if resume.test_total:
                old_total = resume.test_total.total
                resume.test_total.total = round((old_total * 0.5) + (new_total * 0.5), 2)

                # Разбираем существующее justification на уже упомянутые названия
                existing_justification = resume.test_total.justification or ""
                existing_titles = set()
                for part in existing_justification.split("<<"):
                    if ">>" in part:
                        title = part.split(">>")[0].strip()
                        existing_titles.add(title)

                # Добавляем только новые, которых ещё нет
                unique_new_titles = new_titles - existing_titles
                if unique_new_titles:
                    addition = ", ".join(f"<<{title}>>" for title in unique_new_titles)
                    if "опросникам" in existing_justification:
                        resume.test_total.justification += f", {addition}"
                    else:
                        resume.test_total.justification = (
                            "Итоговый результат по таким опросникам как: " + addition
                        )

            else:
                titles_joined = ", ".join(f"<<{title}>>" for title in title_name)
                justification_text = (
                    f"Итоговый результат по таким опросникам как: {titles_joined}"
                )
                resume.test_total = TestTotal(
                    total=new_total,
                    justification=justification_text,
                    resume_id=resume_id
                )
        # Обновляем или создаём FeedbackTotal
        if has_feedback and feedback_max > 0:
            new_feedback_total = round((feedback_summary / feedback_max) * 100, 2)
            justification = "Средний балл, рассчитанный по отзывам работодателей"

            if resume.feedback_total:
                old_total = resume.feedback_total.total
                resume.test_total.total = round((old_total * 0.5) + (new_feedback_total * 0.5), 2)
                resume.feedback_total.justification = justification
            else:
                resume.feedback_total = FeedbackTotal(
                    total=new_feedback_total,
                    justification=justification,
                    resume_id=resume_id
                )

        self.db.add_all(skills)
        await self.db.commit()


    async def get_resumes_by_vacancy_sorted(self, vacancy_id: int,user:User) -> list[Resume]:
        # Получаем все резюме, прикреплённые к вакансии
        result = await self.db.execute(
            select(Resume)
            .filter_by(user_id=user.id)
            .join(Resume.job_postings)
            .where(JobPosting.id == vacancy_id)
            .options(
                selectinload(Resume.soft_total),
                selectinload(Resume.hard_total),
                selectinload(Resume.test_total),
                selectinload(Resume.feedback_total)
            )
        )
        resumes = result.scalars().all()

        # Вычисляем рейтинг каждого резюме на основе total значений
        def calculate_total_score(resume: Resume):
            soft_score = resume.soft_total.total if resume.soft_total else 0
            hard_score = resume.hard_total.total if resume.hard_total else 0
            test_score = resume.test_total.total if resume.test_total else 0
            feedback_score = resume.feedback_total.total if resume.feedback_total else 0
            return soft_score + hard_score + test_score + feedback_score

        # Сортировка по сумме всех total (по убыванию)
        sorted_resumes = sorted(resumes, key=calculate_total_score, reverse=True)

        return sorted_resumes
        
    async def get_resume(self, resume_id: int, user: User) -> Resume:
    # Используем selectinload для предзагрузки связанных объектов
        result = await self.db.execute(
            select(Resume)
            .filter_by(id=resume_id, user_id=user.id)
            .options(
                selectinload(Resume.experiences),
                selectinload(Resume.educations),
                selectinload(Resume.skills)
            )
            .where(Resume.id == resume_id)
        )
        resume = result.scalars().first()
        return resume

    async def delete_resume(self, resume_id: int, user: User,commit:bool=True) -> Resume:
        doc_delete = CVService(self.db)
        resume = await self.get_resume(resume_id, user)
        blob_name = f"analysis_reports/{user.id}/{resume_id}/report.pdf"
        gcs_uri = f"gs://{GCS_BUCKET_NAME}/{blob_name}"
        if not resume:
            return None

        # Удаляем запись из БД
        await self.db.delete(resume)

        # 1) Удаляем основной CV, игнорируя 404
        try:
            await doc_delete.delete_blob_from_gcs(resume.cv_gcs_uri)
        except HTTPException as exc:
            if exc.status_code == 404 or "No such object" in str(exc.detail):
                logger.warning(f"CV blob not found in GCS, skipping delete: {resume.cv_gcs_uri}")
            else:
                raise
        except Exception as exc:
            msg = str(exc)
            if "404" in msg and "No such object" in msg:
                logger.warning(f"CV blob not found in GCS (raw error), skipping delete: {resume.cv_gcs_uri}")
            else:
                raise

        # 2) Удаляем отчёт-результат, игнорируя 404
        try:
            await doc_delete.delete_report_from_gcs(gcs_uri)
        except HTTPException as exc:
            if exc.status_code == 404 or "No such object" in str(exc.detail):
                logger.warning(f"Report not found in GCS, skipping delete: {gcs_uri}")
            else:
                raise
        except Exception as exc:
            msg = str(exc)
            if "404" in msg and "No such object" in msg:
                logger.warning(f"Report not found in GCS (raw error), skipping delete: {gcs_uri}")
            else:
                raise

        if commit:
            await self.db.commit()
        return resume


    
    





        