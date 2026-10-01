from fastapi import APIRouter

from app.api.v1 import alunos, auth, motoristas, responsaveis

api_router = APIRouter(prefix="/api/v1")
for r in (auth, responsaveis, motoristas, alunos):
    api_router.include_router(r.router)
