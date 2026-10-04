from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models import Aluno, HistoricoRota, Parada, PresencaViagem, RotaAluno, StatusFrequencia


def montar_presencas(db: Session, viagem: HistoricoRota) -> dict:
    """Checklist da viagem: todos os alunos da rota, na ordem das paradas, com a marcação (ou pendente)."""
    q = (
        select(
            Aluno.id,
            Aluno.nome,
            Aluno.escola,
            RotaAluno.parada_id,
            Parada.nome,
            PresencaViagem.status,
            PresencaViagem.observacao,
            PresencaViagem.registrado_em,
        )
        .select_from(RotaAluno)
        .join(Aluno, Aluno.id == RotaAluno.aluno_id)
        .outerjoin(Parada, Parada.id == RotaAluno.parada_id)
        .outerjoin(
            PresencaViagem,
            and_(
                PresencaViagem.historico_rota_id == viagem.id,
                PresencaViagem.aluno_id == RotaAluno.aluno_id,
            ),
        )
        .where(RotaAluno.rota_id == viagem.rota_id)
        .order_by(Parada.ordem.is_(None), Parada.ordem, Aluno.nome)
    )
    alunos = [
        {
            "aluno_id": a_id,
            "nome": nome,
            "escola": escola,
            "parada_id": parada_id,
            "parada_nome": parada_nome,
            "status": status,
            "observacao": obs,
            "registrado_em": em,
        }
        for a_id, nome, escola, parada_id, parada_nome, status, obs, em in db.execute(q).all()
    ]
    presentes = sum(1 for a in alunos if a["status"] == StatusFrequencia.PRESENTE)
    faltas = sum(1 for a in alunos if a["status"] == StatusFrequencia.FALTA)
    return {
        "viagem_id": viagem.id,
        "status_viagem": viagem.status,
        "total": len(alunos),
        "presentes": presentes,
        "faltas": faltas,
        "pendentes": len(alunos) - presentes - faltas,
        "alunos": alunos,
    }