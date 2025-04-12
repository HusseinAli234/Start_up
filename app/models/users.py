from app.models import Base
from sqlalchemy import String, Integer, Column, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    #todo logo
    name: Mapped[str] = mapped_column(String, index=True)
    about: Mapped[str] = mapped_column(String, index=True)
    address: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[str] = mapped_column(String, index=True)
    phone: Mapped[str] = mapped_column(String, index=True)
    inn: Mapped[str] = mapped_column(String, index=True)
    
