from datetime import date

from pydantic import BaseModel

from app.models import Gravidade


class OcorrenciaRecente(BaseModel):
    id: int
    aluno_nome: str
    tipo_nome: str
    data: date
    gravidade: Gravidade


class DashboardOut(BaseModel):
    alunos_ativos: int
    responsaveis: int
    motoristas: int
    veiculos_ativos: int
    rotas_ativas: int
    viagens_em_andamento: int
    ocorrencias_30_dias: int
    ocorrencias_recentes: list[OcorrenciaRecente]