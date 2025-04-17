import enum
from sqlalchemy.orm import  Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Float, ForeignKey, Enum as SAEnum
from app.models.base import Base
from app.users.models.users import User

class Prompt(Base):
    __tablename__ = "prompt"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    profession_title: Mapped[str] = mapped_column(String,index=True)
    prompt_for_cv:Mapped[str] = mapped_column(String,index=True)
    prompt_for_media:Mapped[str] = mapped_column(String,index=True)