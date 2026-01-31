from fastapi import APIRouter, FastAPI
from src.users.routes import router as users_router
from src.users.auth_routes import router as auth_router

app = FastAPI()

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(users_router)

app.include_router(v1_router)
