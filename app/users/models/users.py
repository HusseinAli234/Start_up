from app.models.base import Base
from sqlalchemy import String, Integer,ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import Boolean, Enum as SQLAlchemyEnum, DateTime
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum






class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, index=True)
    about: Mapped[str] = mapped_column(String, index=True)
    address: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[str] = mapped_column(String, index=True)
    phone: Mapped[str] = mapped_column(String, index=True)
    inn: Mapped[str] = mapped_column(String, index=True)
    logo: Mapped[str] = mapped_column(String, nullable=True, index=True)
    password: Mapped[str] = mapped_column(String, index=True)
    user_type: Mapped[str] = mapped_column(String(20), index=True, nullable=True, default="individual")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True,nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    promocode_entry: Mapped["PromoCode"] = relationship(back_populates="user", uselist=False,cascade="all, delete-orphan",lazy="selectin")

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
    user_test: Mapped[list["SocialTest"]] = relationship(
        "SocialTest",
        back_populates="user",
        cascade="all, delete-orphan",lazy="selectin"
    )

class PromoCode(Base):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),  default=lambda: datetime.now(timezone.utc))
    user_type: Mapped[str] = mapped_column(String)  # "individual" or "company"

    user: Mapped["User"] = relationship(back_populates="promocode_entry",
        cascade="all, delete-orphan",lazy="selectin",single_parent=True)
