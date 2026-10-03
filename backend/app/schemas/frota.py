import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import StatusRota

_PLACA = re.compile(r"^[A-Z]{3}\d[A-Z0-9]\d{2}$")


def _texto_obrigatorio(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("Campo obrigatório")
    return v


def _normalizar_placa(v: str) -> str:
    v = re.sub(r"[\s-]", "", v).upper()
    if not _PLACA.match(v):
        raise ValueError("Placa inválida (use ABC1D23 ou ABC1234)")
    return v


def _vazio_para_none(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    return v or None


# ---------- Veículos ----------
class VeiculoCreate(BaseModel):
    placa: str = Field(max_length=15)
    apelido: str = Field(max_length=60)
    capacidade: int = Field(default=15, gt=0, le=100)

    _placa = field_validator("placa")(_normalizar_placa)
    _apelido = field_validator("apelido")(_texto_obrigatorio)


class VeiculoUpdate(BaseModel):
    placa: str | None = Field(default=None, max_length=15)
    apelido: str | None = Field(default=None, max_length=60)
    capacidade: int | None = Field(default=None, gt=0, le=100)
    ativo: bool | None = None

    @field_validator("placa")
    @classmethod
    def _placa(cls, v):
        return None if v is None else _normalizar_placa(v)

    @field_validator("apelido")
    @classmethod
    def _apelido(cls, v):
        return None if v is None else _texto_obrigatorio(v)


class VeiculoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    placa: str
    apelido: str
    capacidade: int
    ativo: bool


class VeiculoResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    placa: str
    apelido: str


class MotoristaResumo(BaseModel):
    id: int
    nome: str


# ---------- Rotas ----------
class RotaCreate(BaseModel):
    nome: str = Field(max_length=120)
    escola: str | None = Field(default=None, max_length=120)
    veiculo_id: int | None = None
    motorista_id: int | None = None
    status: StatusRota = StatusRota.ATIVA

    _nome = field_validator("nome")(_texto_obrigatorio)
    _escola = field_validator("escola")(_vazio_para_none)


class RotaUpdate(BaseModel):
    nome: str | None = Field(default=None, max_length=120)
    escola: str | None = Field(default=None, max_length=120)
    veiculo_id: int | None = None
    motorista_id: int | None = None
    status: StatusRota | None = None

    @field_validator("nome")
    @classmethod
    def _nome(cls, v):
        return None if v is None else _texto_obrigatorio(v)

    _escola = field_validator("escola")(_vazio_para_none)


class ParadaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rota_id: int
    nome: str
    latitude: float
    longitude: float
    ordem: int


class RotaAlunoOut(BaseModel):
    aluno_id: int
    nome: str
    escola: str
    parada_id: int | None
    parada_nome: str | None


class RotaOut(BaseModel):
    id: int
    nome: str
    escola: str | None
    status: StatusRota
    veiculo: VeiculoResumo | None
    motorista: MotoristaResumo | None
    total_paradas: int
    total_alunos: int


class RotaDetalheOut(RotaOut):
    paradas: list[ParadaOut]
    alunos: list[RotaAlunoOut]


# ---------- Paradas ----------
class ParadaCreate(BaseModel):
    nome: str = Field(max_length=120)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    ordem: int | None = Field(default=None, ge=1)

    _nome = field_validator("nome")(_texto_obrigatorio)


class ParadaUpdate(BaseModel):
    nome: str | None = Field(default=None, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("nome")
    @classmethod
    def _nome(cls, v):
        return None if v is None else _texto_obrigatorio(v)


class ParadaReordenar(BaseModel):
    ids: list[int]


# ---------- Alunos na rota ----------
class RotaAlunoCreate(BaseModel):
    aluno_id: int
    parada_id: int | None = None


class RotaAlunoUpdate(BaseModel):
    parada_id: int | None = None