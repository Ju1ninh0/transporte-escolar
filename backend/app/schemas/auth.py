from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Perfil


class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    email: EmailStr
    telefone: str | None
    perfil: Perfil
