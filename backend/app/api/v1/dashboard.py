from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import admin_only
from app.db.session import get_db
from app.models import (
    Aluno,
    HistoricoRota,
    Motorista,
    Ocorrencia,
    Responsavel,
    Rota,
    StatusExecucao,
    StatusRota,
    TipoOcorrencia,
    Usuario,
    Veiculo,
)
from app.schemas.dashboard import DashboardOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _contar(db: Session, consulta) -> int:
    return db.scalar(consulta) or 0


@router.get("", response_model=DashboardOut)
def painel(db: Session = Depends(get_db), user: Usuario = Depends(admin_only)):
    emp = user.empresa_id
    hoje = date.today()
    desde = hoje - timedelta(days=30)
    recentes = db.execute(
        select(Ocorrencia, Aluno.nome, TipoOcorrencia.nome)
        .join(Aluno, Aluno.id == Ocorrencia.aluno_id)
        .join(TipoOcorrencia, TipoOcorrencia.id == Ocorrencia.tipo_id)
        .where(Aluno.empresa_id == emp)
        .order_by(Ocorrencia.data.desc(), Ocorrencia.id.desc())
        .limit(5)
    ).all()
    return {
        "alunos_ativos": _contar(
            db, select(func.count(Aluno.id)).where(Aluno.empresa_id == emp, Aluno.ativo.is_(True))
        ),
        "responsaveis": _contar(db, select(func.count(Responsavel.id)).where(Responsavel.empresa_id == emp)),
        "motoristas": _contar(db, select(func.count(Motorista.id)).where(Motorista.empresa_id == emp)),
        "veiculos_ativos": _contar(
            db, select(func.count(Veiculo.id)).where(Veiculo.empresa_id == emp, Veiculo.ativo.is_(True))
        ),
        "rotas_ativas": _contar(
            db, select(func.count(Rota.id)).where(Rota.empresa_id == emp, Rota.status == StatusRota.ATIVA)
        ),
        "viagens_em_andamento": _contar(
            db,
            select(func.count(HistoricoRota.id))
            .join(Rota, Rota.id == HistoricoRota.rota_id)
            .where(Rota.empresa_id == emp, HistoricoRota.status == StatusExecucao.EM_ANDAMENTO),
        ),
        "ocorrencias_30_dias": _contar(
            db,
            select(func.count(Ocorrencia.id))
            .join(Aluno, Aluno.id == Ocorrencia.aluno_id)
            .where(Aluno.empresa_id == emp, Ocorrencia.data >= desde, Ocorrencia.data <= hoje),
        ),
        "ocorrencias_recentes": [
            {
                "id": o.id,
                "aluno_nome": aluno_nome,
                "tipo_nome": tipo_nome,
                "data": o.data,
                "gravidade": o.gravidade,
            }
            for o, aluno_nome, tipo_nome in recentes
        ],
    }