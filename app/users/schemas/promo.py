from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PromoCodeBase(BaseModel):
    code: str
    user_type: str  # "individual" или "company"

class PromoCodeCreate(PromoCodeBase):
    pass

class PromoCodeInDB(PromoCodeBase):
    id: int
    activated_by_user_id: Optional[int] = None
    created_at: datetime

    class Config:
        orm_mode = True
