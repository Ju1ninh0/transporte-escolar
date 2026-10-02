from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import Gravidade


def _texto_obrigatorio(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("Campo obrigatório")
    return v


class TipoOcorrenciaCreate(BaseModel):
    nome: str = Field(max_length=80)

    _nome = field_validator("nome")(_texto_obrigatorio)


class TipoOcorrenciaUpdate(BaseModel):
    nome: str | None = Field(default=None, max_length=80)
    ativo: bool | None = None

    @field_validator("nome")
    @classmethod
    def _nome(cls, v):
        return None if v is None else _texto_obrigatorio(v)


class TipoOcorrenciaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    ativo: bool


class OcorrenciaCreate(BaseModel):
    aluno_id: int
    tipo_id: int
    data: date
    gravidade: Gravidade
    descricao: str
    consequencia: str | None = Field(default=None, max_length=120)

    _descricao = field_validator("descricao")(_texto_obrigatorio)


class OcorrenciaUpdate(BaseModel):
    # aluno não pode ser trocado
    tipo_id: int | None = None
    data: date | None = None
    gravidade: Gravidade | None = None
    descricao: str | None = None
    consequencia: str | None = Field(default=None, max_length=120)

    @field_validator("descricao")
    @classmethod
    def _descricao(cls, v):
        return None if v is None else _texto_obrigatorio(v)


class OcorrenciaOut(BaseModel):
    id: int
    aluno_id: int
    aluno_nome: str
    tipo_id: int
    tipo_nome: str
    data: date
    gravidade: Gravidade
    descricao: str
    consequencia: str | None
    registrado_por: int
    registrado_por_nome: str
    created_at: datetime


class SugestaoConsequencia(BaseModel):
    aluno_id: int
    numero_ocorrencia: int
    consequencia: str | None