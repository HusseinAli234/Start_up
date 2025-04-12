from app.models.base import Base
from sqlalchemy import String, Integer
from sqlalchemy.orm import relationship, Mapped, mapped_column




class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, index=True)
    about: Mapped[str] = mapped_column(String, index=True)
    address: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[str] = mapped_column(String, index=True)
    phone: Mapped[str] = mapped_column(String, index=True)
    inn: Mapped[str] = mapped_column(String, index=True)
    # Реализация логотипа — можно хранить URL или путь к файлу
    logo: Mapped[str] = mapped_column(String, nullable=True, index=True)
    password: Mapped[str] = mapped_column(String, index=True)
 
    user_resumes: Mapped[list["Resume"]] = relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",lazy="selectin"
    )
    user_job_postings: Mapped[list["JobPosting"]] = relationship(
        "JobPosting",
        back_populates="user",
        cascade="all, delete-orphan",lazy="selectin"
    )