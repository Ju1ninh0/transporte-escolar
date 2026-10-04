from datetime import datetime

from pydantic import BaseModel, Field


class LocalizacaoIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    velocidade: float | None = Field(default=None, ge=0, le=200)  # m/s
    direcao: float | None = Field(default=None, ge=0, le=360)  # graus


class PosicaoOut(BaseModel):
    latitude: float
    longitude: float
    velocidade: float | None
    direcao: float | None
    timestamp: datetime


class LocalizacaoOut(PosicaoOut):
    id: int
    viagem_id: int


class ViagemAtivaOut(BaseModel):
    viagem_id: int
    rota_id: int
    rota_nome: str
    veiculo_apelido: str | None
    veiculo_placa: str | None
    motorista_nome: str | None
    iniciada_em: datetime
    posicao: PosicaoOut | None


class PontoTrilhaOut(BaseModel):
    latitude: float
    longitude: float
    timestamp: datetime