from sqlalchemy.orm import Session
from app.models.job_seekers import Resume,Education,Experience,Skill  # Assuming a Resume model exists
from app.schemas.resume_schema import ResumeCreate  # Assuming schemas exist

class ResumeService:
    def __init__(self, db: Session):
        self.db = db

    def create_resume(self, resume_data: ResumeCreate):
        db_resume = Resume(
        fullname=resume_data.fullname,
        location=resume_data.location,
        experiences=[Experience(name=experience.name, description=experience.description) for experience in resume_data.experience],
        educations=[Education(name=education.name, description=education.description) for education in resume_data.education],
        skills=[Skill(title=skill.title, level=skill.level,justification=skill.justification,type=skill.type) for skill in resume_data.skills]
    )
        self.db.add(db_resume)
        self.db.commit()
        self.db.refresh(db_resume)
        return db_resume

    def get_resume(self, resume_id: int):
        # Retrieve a resume by ID
        return self.db.query(Resume).filter(Resume.id == resume_id).first()

    # def update_resume(self, resume_id: int, resume_data: ResumeUpdate):
    #     resume = self.get_resume(resume_id)
    #     if not resume:
    #         return None
    #     for key, value in resume_data.dict(exclude_unset=True).items():
    #         setattr(resume, key, value)
    #     self.db.commit()
    #     self.db.refresh(resume)
    #     return resume

    def delete_resume(self, resume_id: int):
        resume = self.get_resume(resume_id)
        if not resume:
            return None
        self.db.delete(resume)
        self.db.commit()
        return resume
