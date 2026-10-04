from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import Gravidade, StatusFrequencia
from app.schemas.frota import ParadaOut
from app.schemas.gps import PosicaoOut


class FilhoRota(BaseModel):
    rota_id: int
    rota_nome: str
    parada_id: int | None
    parada_nome: str | None
    viagem_em_andamento_id: int | None


class FilhoOut(BaseModel):
    id: int
    nome: str
    escola: str
    serie: str | None
    rotas: list[FilhoRota]


class ViagemDoFilho(BaseModel):
    viagem_id: int
    iniciada_em: datetime
    motorista_nome: str | None
    posicao: PosicaoOut | None
    status_chamada: StatusFrequencia | None


class RotaAcompanhamento(BaseModel):
    rota_id: int
    rota_nome: str
    escola: str | None
    veiculo_apelido: str | None
    veiculo_placa: str | None
    motorista_nome: str | None
    parada_id: int | None
    parada_nome: str | None
    paradas: list[ParadaOut]
    viagem: ViagemDoFilho | None


class AcompanhamentoOut(BaseModel):
    aluno_id: int
    aluno_nome: str
    rotas: list[RotaAcompanhamento]


class PresencaRegistro(BaseModel):
    viagem_id: int
    iniciada_em: datetime
    rota_nome: str
    status: StatusFrequencia
    observacao: str | None


class PresencaHistoricoOut(BaseModel):
    aluno_id: int
    aluno_nome: str
    dias: int
    presentes: int
    faltas: int
    registros: list[PresencaRegistro]


class PixOut(BaseModel):
    recebedor: str
    tipo_chave: str
    chave: str
    mensagem: str | None = None


class OcorrenciaFilhoOut(BaseModel):
    id: int
    aluno_id: int
    aluno_nome: str
    tipo_nome: str
    data: date
    gravidade: Gravidade
    descricao: str
    consequencia: str | None


class AvisoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tipo: str
    titulo: str
    mensagem: str
    lida: bool
    created_at: datetime


class ResumoAvisos(BaseModel):
    nao_lidas: int


class ComunicadoIn(BaseModel):
    titulo: str = Field(max_length=120)
    mensagem: str = Field(max_length=2000)
    rota_id: int | None = None  # None = todos os responsáveis da empresa

    @field_validator("titulo", "mensagem")
    @classmethod
    def _obrigatorio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Campo obrigatório")
        return v


class ComunicadoOut(BaseModel):
    destinatarios: int