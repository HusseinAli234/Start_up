from sqlalchemy.orm import Session
from app import models, schemas

def create_resume(db: Session, resume_data: schemas.ResumeCreate):
    resume = models.Resume(
        fullname=resume_data.fullname,
        location=resume_data.location,
        experience=resume_data.experience,
        education=resume_data.education
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    for skill in resume_data.skills:
        new_skill = models.Skill(title=skill.title, level=skill.level, resume_id=resume.id)
        db.add(new_skill)

    db.commit()
    db.refresh(resume)
    return resume

def get_resume(db: Session, resume_id: int):
    return db.query(models.Resume).filter(models.Resume.id == resume_id).first()
