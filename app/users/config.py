from authx import AuthX, AuthXConfig
from .models import User
from sqlalchemy.future import select
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException
from fastapi import Request
from jose import jwt, JWTError
from datetime import datetime, timedelta


config = AuthXConfig()
config.JWT_SECRET_KEY = "SECRET_KEY"
config.JWT_ACCESS_COOKIE_NAME = "my_access_token"
config.JWT_REFRESH_COOKIE_NAME = "my_refresh_token"
config.JWT_COOKIE_CSRF_PROTECT = False
config.JWT_COOKIE_SAMESITE = "None"
config.JWT_COOKIE_SECURE = True
config.JWT_TOKEN_LOCATION = ["cookies", "headers"]
security = AuthX(config, model=User)



async def safe_get_current_subject(request: Request) -> User:
    # 1. Пробуем взять токен из cookie
    token = request.cookies.get(config.JWT_ACCESS_COOKIE_NAME)

    # 2. Если нет — пробуем из заголовка Authorization
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split("Bearer ")[1].strip()
    
    # 3. Если всё равно нет токена — ошибка
    if not token:
        raise HTTPException(status_code=401, detail="Нет токена")

    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=["HS256"])
        uid = payload.get("sub")
        if uid is None:
            raise HTTPException(status_code=401, detail="Неверный токен")
    except JWTError:
        raise HTTPException(status_code=401, detail="Недействительный токен")

    db = await anext(get_db())
    try:
        result = await db.execute(select(User).filter_by(id=uid))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        return user
    finally:
        await db.aclose()

