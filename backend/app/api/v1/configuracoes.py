from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import admin_only
from app.db.session import get_db
from app.models import Configuracao, RegraReincidencia, Usuario
from app.schemas.configuracao import (
    ConfiguracoesOut, ConfiguracoesUpdate, RegraOut, RegraUpdate,
)

router = APIRouter(prefix="/configuracoes", tags=["configuracoes"])


def _get(db: Session, empresa_id: int, chave: str) -> Configuracao | None:
    return db.scalar(
        select(Configuracao).where(Configuracao.empresa_id == empresa_id, Configuracao.chave == chave)
    )


def _set(db: Session, empresa_id: int, chave: str, valor: dict) -> None:
    cfg = _get(db, empresa_id, chave)
    if cfg is None:
        db.add(Configuracao(empresa_id=empresa_id, chave=chave, valor=valor))
    else:
        cfg.valor = valor  # novo dict: garante que o JSON seja marcado como alterado


def _montar(db: Session, empresa_id: int) -> ConfiguracoesOut:
    pix = _get(db, empresa_id, "pix")
    prox = _get(db, empresa_id, "proximidade_metros")
    regras = db.scalars(
        select(RegraReincidencia)
        .where(RegraReincidencia.empresa_id == empresa_id)
        .order_by(RegraReincidencia.numero_ocorrencia)
    ).all()
    return ConfiguracoesOut(
        pix=pix.valor if pix else None,
        proximidade_metros=(prox.valor or {}).get("metros") if prox else None,
        regras_reincidencia=[
            RegraOut(numero_ocorrencia=r.numero_ocorrencia, consequencia=r.consequencia)
            for r in regras
        ],
    )


@router.get("", response_model=ConfiguracoesOut)
def consultar(db: Session = Depends(get_db), user: Usuario = Depends(admin_only)):
    return _montar(db, user.empresa_id)


@router.patch("", response_model=ConfiguracoesOut)
def atualizar(
    body: ConfiguracoesUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    if body.pix is not None:
        _set(db, user.empresa_id, "pix", body.pix.model_dump())
    if body.proximidade_metros is not None:
        _set(db, user.empresa_id, "proximidade_metros", {"metros": body.proximidade_metros})
    db.commit()
    return _montar(db, user.empresa_id)


@router.patch("/regras-reincidencia/{numero}", response_model=ConfiguracoesOut)
def atualizar_regra(
    numero: int,
    body: RegraUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    regra = db.scalar(
        select(RegraReincidencia).where(
            RegraReincidencia.empresa_id == user.empresa_id,
            RegraReincidencia.numero_ocorrencia == numero,
        )
    )
    if regra is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Regra de reincidência não encontrada")
    regra.consequencia = body.consequencia
    db.commit()
    return _montar(db, user.empresa_id)