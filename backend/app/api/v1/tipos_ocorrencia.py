from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import admin_only
from app.db.session import get_db
from app.models import TipoOcorrencia, Usuario
from app.schemas.ocorrencia import TipoOcorrenciaCreate, TipoOcorrenciaOut, TipoOcorrenciaUpdate

router = APIRouter(prefix="/tipos-ocorrencia", tags=["tipos-ocorrencia"])


def _nome_duplicado(db: Session, empresa_id: int, nome: str, ignorar_id: int | None = None) -> bool:
    q = select(TipoOcorrencia.id).where(
        TipoOcorrencia.empresa_id == empresa_id,
        func.lower(TipoOcorrencia.nome) == nome.lower(),
    )
    if ignorar_id is not None:
        q = q.where(TipoOcorrencia.id != ignorar_id)
    return db.scalar(q) is not None


@router.get("", response_model=list[TipoOcorrenciaOut])
def listar(
    ativo: bool | None = None,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    q = select(TipoOcorrencia).where(TipoOcorrencia.empresa_id == user.empresa_id)
    if ativo is not None:
        q = q.where(TipoOcorrencia.ativo == ativo)
    return db.scalars(q.order_by(TipoOcorrencia.nome)).all()


@router.post("", response_model=TipoOcorrenciaOut, status_code=status.HTTP_201_CREATED)
def criar(
    body: TipoOcorrenciaCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    if _nome_duplicado(db, user.empresa_id, body.nome):
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um tipo com esse nome")
    tipo = TipoOcorrencia(empresa_id=user.empresa_id, nome=body.nome)
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return tipo


@router.patch("/{tipo_id}", response_model=TipoOcorrenciaOut)
def atualizar(
    tipo_id: int,
    body: TipoOcorrenciaUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    tipo = db.scalar(
        select(TipoOcorrencia).where(
            TipoOcorrencia.id == tipo_id, TipoOcorrencia.empresa_id == user.empresa_id
        )
    )
    if tipo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tipo de ocorrência não encontrado")
    dados = body.model_dump(exclude_unset=True)
    if dados.get("nome") is None:
        dados.pop("nome", None)
    if dados.get("ativo") is None:
        dados.pop("ativo", None)
    if "nome" in dados and _nome_duplicado(db, user.empresa_id, dados["nome"], tipo.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um tipo com esse nome")
    for k, v in dados.items():
        setattr(tipo, k, v)
    db.commit()
    db.refresh(tipo)
    return tipo