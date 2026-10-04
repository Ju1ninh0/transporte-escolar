from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models import StatusExecucao, StatusFrequencia


class PresencaIn(BaseModel):
    status: StatusFrequencia
    observacao: str | None = Field(default=None, max_length=255)

    @field_validator("observacao")
    @classmethod
    def _obs(cls, v):
        if v is None:
            return None
        v = v.strip()
        return v or None


class PresencaAlunoOut(BaseModel):
    aluno_id: int
    nome: str
    escola: str
    parada_id: int | None
    parada_nome: str | None
    status: StatusFrequencia | None
    observacao: str | None
    registrado_em: datetime | None


class PresencasOut(BaseModel):
    viagem_id: int
    status_viagem: StatusExecucao
    total: int
    presentes: int
    faltas: int
    pendentes: int
    alunos: list[PresencaAlunoOut]