from datetime import datetime

from pydantic import BaseModel

from app.models import StatusExecucao
from app.schemas.frota import ParadaOut, RotaAlunoOut, RotaOut


class ViagemOut(BaseModel):
    id: int
    rota_id: int
    rota_nome: str
    veiculo_id: int | None
    motorista_id: int | None
    motorista_nome: str | None
    iniciada_em: datetime
    finalizada_em: datetime | None
    status: StatusExecucao


class MotoristaRotaOut(RotaOut):
    viagem_em_andamento_id: int | None = None


class MotoristaRotaDetalheOut(MotoristaRotaOut):
    paradas: list[ParadaOut]
    alunos: list[RotaAlunoOut]