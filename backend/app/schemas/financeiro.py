from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import StatusMensalidade


class MetodoPagamento(str, Enum):
    PIX = "PIX"
    DINHEIRO = "DINHEIRO"
    TRANSFERENCIA = "TRANSFERENCIA"
    OUTRO = "OUTRO"


class MensalidadeCreate(BaseModel):
    aluno_id: int
    mes_referencia: date
    vencimento: date
    valor: Decimal = Field(gt=0, max_digits=10, decimal_places=2)

    @field_validator("mes_referencia", mode="before")
    @classmethod
    def normaliza_mes(cls, v):
        if isinstance(v, str) and len(v) == 7:
            v = f"{v}-01"
        if isinstance(v, str):
            v = date.fromisoformat(v)
        return v.replace(day=1)


class MensalidadeUpdate(BaseModel):
    valor: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    vencimento: date | None = None
    status: StatusMensalidade | None = None


class PagamentoCreate(BaseModel):
    # sem gt=0 de proposito: valor <= 0 e rejeitado no router com 400
    valor: Decimal = Field(max_digits=10, decimal_places=2)
    data_pagamento: date
    metodo: MetodoPagamento
    comprovante: str | None = Field(default=None, max_length=255)
    provider_ref: str | None = Field(default=None, max_length=120)


class PagamentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    mensalidade_id: int
    valor: Decimal
    data_pagamento: date | None
    metodo: str
    comprovante: str | None
    created_at: datetime


class MensalidadeOut(BaseModel):
    id: int
    aluno_id: int
    aluno_nome: str
    responsavel_id: int
    responsavel_nome: str
    mes_referencia: date
    valor: Decimal
    valor_pago: Decimal
    saldo: Decimal
    vencimento: date
    status: StatusMensalidade
    created_at: datetime
    updated_at: datetime


class MensalidadeDetalhe(MensalidadeOut):
    pagamentos: list[PagamentoOut]


class ResumoFinanceiro(BaseModel):
    total_previsto: Decimal
    total_recebido: Decimal
    total_pendente: Decimal
    total_atrasado: Decimal