from fastapi import FastAPI
from app.routers import users
from app.database import Base, engine


app = FastAPI()

app.include_router(users.router)
Base.metadata.create_all(bind=engine)
@app.get("/")
def read_root():
    return {"message" : "Добро пожаловать!"}