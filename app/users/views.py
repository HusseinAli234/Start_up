from .models import User
from .schemas import UserBase, UserLoginSChema, UserCreate
from .config import security, config
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext
from app.database import get_db
from .models import User 
from .schemas import UserBase, UserLoginSChema
from .config import security, config

# Создаем контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register")
async def register(user: UserCreate, response: Response, db: AsyncSession = Depends(get_db)):

    stmt = select(User).filter_by(email=user.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
    
    # Хешируем пароль
    hashed_password = pwd_context.hash(user.password)
    
    # Создаем нового пользователя, передаем хеш пароля в поле password
    new_user = User(
        name=user.name,
        about=user.about,
        address=user.address,
        email=user.email,
        phone=user.phone,
        inn=user.inn,
        logo=user.logo,
        password=hashed_password  # Используем password для хранения хешированного пароля
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Сразу после регистрации создаем токен
    token = security.create_access_token(
        uid=str(new_user.id), 
        subject={"email": new_user.email})

    # Устанавливаем токен в cookie
    response.set_cookie(
        key=config.JWT_ACCESS_COOKIE_NAME,
        value=token,
        httponly=True
    )

    return {"message": "Пользователь успешно зарегистрирован и залогинен"}



@router.post("/login")
async def login(user: UserLoginSChema, response: Response, db: AsyncSession = Depends(get_db)):
    
    stmt = select(User).filter_by(email=user.email)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()
    if not db_user or not pwd_context.verify(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    
    
    token = security.create_access_token(uid=str(db_user.id), subject={"email": db_user.email})
    
    # Устанавливаем токен в виде HTTP-only cookie
    response.set_cookie(
        key=config.JWT_ACCESS_COOKIE_NAME,
        value=token,
        httponly=True
    )
    
    return {"message": "Логин успешен"}


@router.post("/logout")
async def logout(response: Response):
    
    response.delete_cookie(key=config.JWT_ACCESS_COOKIE_NAME)
    return {"message": "Логаут успешен"}
