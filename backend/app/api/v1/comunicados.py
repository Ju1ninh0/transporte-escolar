from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import admin_only
from app.db.session import get_db
from app.models import Aluno, Notificacao, Perfil, Responsavel, Rota, RotaAluno, Usuario
from app.schemas.responsavel import ComunicadoIn, ComunicadoOut

router = APIRouter(prefix="/comunicados", tags=["comunicados"])


@router.post("", response_model=ComunicadoOut, status_code=status.HTTP_201_CREATED)
def enviar(body: ComunicadoIn, db: Session = Depends(get_db), user: Usuario = Depends(admin_only)):
    q = select(Usuario.id).where(
        Usuario.empresa_id == user.empresa_id,
        Usuario.perfil == Perfil.RESPONSAVEL,
        Usuario.ativo.is_(True),
    )
    if body.rota_id is not None:
        rota = db.scalar(
            select(Rota.id).where(Rota.id == body.rota_id, Rota.empresa_id == user.empresa_id)
        )
        if rota is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Rota não encontrada")
        q = (
            q.join(Responsavel, Responsavel.usuario_id == Usuario.id)
            .join(Aluno, Aluno.responsavel_id == Responsavel.id)
            .join(RotaAluno, RotaAluno.aluno_id == Aluno.id)
            .where(RotaAluno.rota_id == body.rota_id, Aluno.ativo.is_(True))
        )
    destinatarios = sorted(set(db.scalars(q).all()))
    if not destinatarios:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nenhum responsável para receber o aviso")
    db.add_all(
        Notificacao(usuario_id=uid, tipo="COMUNICADO", titulo=body.titulo, mensagem=body.mensagem)
        for uid in destinatarios
    )
    db.commit()
    return {"destinatarios": len(destinatarios)}