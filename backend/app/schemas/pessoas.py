from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PessoaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    telefone: str | None = Field(default=None, max_length=20)
    senha: str = Field(min_length=8, max_length=128)


class ResponsavelCreate(PessoaCreate):
    endereco: str | None = Field(default=None, max_length=255)


class ResponsavelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    usuario_id: int
    endereco: str | None


class MotoristaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    usuario_id: int


class AlunoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    data_nascimento: date
    escola: str = Field(min_length=2, max_length=120)
    serie: str | None = Field(default=None, max_length=40)
    responsavel_id: int


class AlunoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    data_nascimento: date | None = None
    escola: str | None = Field(default=None, min_length=2, max_length=120)
    serie: str | None = Field(default=None, max_length=40)
    responsavel_id: int | None = None


class AlunoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    data_nascimento: date
    escola: str
    serie: str | None
    responsavel_id: int
    ativo: bool
