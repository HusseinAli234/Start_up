from .models import User
from .schemas import UserBase, UserLoginSChema, UserCreate
from .config import security, config
from fastapi import APIRouter, Depends, HTTPException, Response,Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext
from app.database import get_db
from .models import User
from app.users.models.users import PromoCode
from .schemas import UserBase, UserLoginSChema
from .config import security, config
from jose import jwt, JWTError
from sqlalchemy.orm import selectinload
import os
from datetime import datetime,timedelta,timezone
from dotenv import load_dotenv
from sqlalchemy import update

load_dotenv(override=True)
EMP_PROMO = os.getenv("PROMO_CODE_INDIVIDUAL")
IND_PROMO = os.getenv("PROMO_CODE_COMPANY")
# Создаем контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/auth", tags=["Authentication"])
async def get_token_from_request(request: Request, token_name: str = None) -> str | None:
    token = None
    # 1. Пробуем куки
    if token_name:
        token = request.cookies.get(token_name)

    # 2. Пробуем из заголовка
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split("Bearer ")[1].strip()
    
    return token
@router.post("/register")
async def register(user: UserCreate, response: Response, db: AsyncSession = Depends(get_db)):
    if user.user_type == "individual" and user.promo_code != IND_PROMO:
        raise HTTPException(status_code=400, detail="Неверный промокод для физ. лица")
    if user.user_type == "company" and user.promo_code != EMP_PROMO:
        raise HTTPException(status_code=400, detail="Неверный промокод для юр. лица")

    stmt = select(User).filter_by(email=user.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
    
    # Хешируем пароль
    hashed_password = pwd_context.hash(user.password)
    now = datetime.now(timezone.utc)

    if user.user_type == "individual":
        is_active = True
        expires_at = now + timedelta(hours=2)
    else:
        is_active = False
        expires_at = None  # активация вручную

    
    # Создаем нового пользователя, передаем хеш пароля в поле password
    new_user = User(
        name=user.name,
        about=user.about,
        address=user.address,
        email=user.email,
        phone=user.phone,
        inn=user.inn,
        logo=user.logo,
        password=hashed_password , # Используем password для хранения хешированного пароля
        is_active=is_active,
        user_type=user.user_type,
        expires_at=expires_at,

    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    promo = PromoCode(
        code=user.promo_code,
        user_id=new_user.id,
        user_type=user.user_type,
    )
    db.add(promo)
    await db.commit()
    await db.refresh(promo)


    
    # Сразу после регистрации создаем токен
    token = security.create_access_token(
        uid=str(new_user.id), 
        subject={"email": new_user.email})
    refresh_token = security.create_refresh_token(uid=str(new_user.id), subject={"email": new_user.email})


    # Устанавливаем токен в cookie
    response.set_cookie(
        key=config.JWT_ACCESS_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="none"
    )
    response.set_cookie(
        key=config.JWT_REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=config.JWT_REFRESH_TOKEN_EXPIRES
    )
    return {"message": "Пользователь успешно зарегистрирован и залогинен",
             "access_token": token,
            "refresh_token": refresh_token,
            "token_type": "bearer"}



@router.post("/login")
async def login(user: UserLoginSChema, response: Response, db: AsyncSession = Depends(get_db)):
    
    stmt = select(User).filter_by(email=user.email)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()
    if not db_user or not pwd_context.verify(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    
    if not db_user.is_active:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Срок действия промокода истек или аккаунт не активирован!")
    
    
    token = security.create_access_token(uid=str(db_user.id), subject={"email": db_user.email})
    refresh_token = security.create_refresh_token(uid=str(db_user.id), subject={"email": db_user.email})

    # Устанавливаем токен в виде HTTP-only cookie
    response.set_cookie(
        key=config.JWT_ACCESS_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="none"
    )
    response.set_cookie(
        key=config.JWT_REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=config.JWT_REFRESH_TOKEN_EXPIRES
    )

    return {"message": "Логин успешен",
             "access_token": token,
    "refresh_token": refresh_token,
    "token_type": "bearer"}

@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    token =  await get_token_from_request(request, config.JWT_REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Нет refresh токена")
    
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=["HS256"])
        uid = payload.get("sub")
        if uid is None:
            raise HTTPException(status_code=401, detail="Неверный refresh токен")
    except JWTError:
        raise HTTPException(status_code=401, detail="Недействительный refresh токен")
    
    new_access_token = security.create_access_token(uid=uid)
    response.set_cookie(
        key=config.JWT_ACCESS_COOKIE_NAME,
        value=new_access_token,
        httponly=True,
        samesite="none",
        secure=True,
    )
    return {"message": "Access token обновлён",
             "access_token": token
            }
@router.post("/activate_promo")
async def activate(email:str,db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    stmt = select(User).filter_by(email=email)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    await db.execute(
                update(User)
                .where(User.email == email)
                .values( is_active=True,
        expires_at=now + timedelta(days=5))
            )
    await db.commit()
    return {f"Пользователь с почтой-{email} активирован"}




@router.get("/me", response_model=UserBase)
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    token = await get_token_from_request(request, config.JWT_ACCESS_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Access токен не найден")

    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=["HS256"])
        uid = payload.get("sub")
        if uid is None:
            raise HTTPException(status_code=401, detail="Неверный access токен")
    except JWTError:
        raise HTTPException(status_code=401, detail="Недействительный access токен")

    stmt = select(User).where(User.id == int(uid)).options(
        selectinload(User.user_resumes),
        selectinload(User.user_job_postings),
        selectinload(User.user_test)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return user
@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=config.JWT_ACCESS_COOKIE_NAME)
    response.delete_cookie(key=config.JWT_REFRESH_COOKIE_NAME)
    return {"message": "Логаут успешен"}



