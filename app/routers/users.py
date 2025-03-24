from fastapi import APIRouter

router = APIRouter(prefix="/v1/api/users",tags=["Users"])

@router.get("/")
def get_users():
    return[{"id":1,"name":"Alice"},{"id":2,"name":"Mark"}]
