from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import admin_only
from app.db.session import get_db
from app.models import Rota, StatusRota, Usuario, Veiculo
from app.schemas.frota import VeiculoCreate, VeiculoOut, VeiculoUpdate
from app.services.frota import total_alunos

router = APIRouter(prefix="/veiculos", tags=["veiculos"])


def _obter(db: Session, user: Usuario, veiculo_id: int) -> Veiculo:
    veiculo = db.scalar(
        select(Veiculo).where(Veiculo.id == veiculo_id, Veiculo.empresa_id == user.empresa_id)
    )
    if veiculo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Veículo não encontrado")
    return veiculo


def _placa_duplicada(
    db: Session, empresa_id: int, placa: str, ignorar_id: int | None = None
) -> bool:
    q = select(Veiculo.id).where(Veiculo.empresa_id == empresa_id, Veiculo.placa == placa)
    if ignorar_id is not None:
        q = q.where(Veiculo.id != ignorar_id)
    return db.scalar(q.limit(1)) is not None


@router.get("", response_model=list[VeiculoOut])
def listar(
    ativo: bool | None = None,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    q = select(Veiculo).where(Veiculo.empresa_id == user.empresa_id)
    if ativo is not None:
        q = q.where(Veiculo.ativo == ativo)
    return db.scalars(q.order_by(Veiculo.apelido)).all()


@router.get("/{veiculo_id}", response_model=VeiculoOut)
def detalhar(veiculo_id: int, db: Session = Depends(get_db), user: Usuario = Depends(admin_only)):
    return _obter(db, user, veiculo_id)


@router.post("", response_model=VeiculoOut, status_code=status.HTTP_201_CREATED)
def criar(body: VeiculoCreate, db: Session = Depends(get_db), user: Usuario = Depends(admin_only)):
    if _placa_duplicada(db, user.empresa_id, body.placa):
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um veículo com essa placa")
    veiculo = Veiculo(
        empresa_id=user.empresa_id,
        placa=body.placa,
        apelido=body.apelido,
        capacidade=body.capacidade,
    )
    db.add(veiculo)
    db.commit()
    db.refresh(veiculo)
    return veiculo


@router.patch("/{veiculo_id}", response_model=VeiculoOut)
def atualizar(
    veiculo_id: int,
    body: VeiculoUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    veiculo = _obter(db, user, veiculo_id)
    dados = body.model_dump(exclude_unset=True)
    for campo in ("placa", "apelido", "capacidade", "ativo"):
        if dados.get(campo) is None:
            dados.pop(campo, None)

    if "placa" in dados and _placa_duplicada(db, user.empresa_id, dados["placa"], veiculo.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um veículo com essa placa")

    if dados.get("ativo") is False and veiculo.ativo:
        em_rota_ativa = db.scalar(
            select(Rota.id)
            .where(Rota.veiculo_id == veiculo.id, Rota.status == StatusRota.ATIVA)
            .limit(1)
        )
        if em_rota_ativa is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Veículo vinculado a uma rota ativa; remova o vínculo antes de desativar",
            )

    if "capacidade" in dados:
        for rota_id in db.scalars(select(Rota.id).where(Rota.veiculo_id == veiculo.id)).all():
            if total_alunos(db, rota_id) > dados["capacidade"]:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Capacidade menor que o total de alunos de uma rota que usa este veículo",
                )

    for k, v in dados.items():
        setattr(veiculo, k, v)
    db.commit()
    db.refresh(veiculo)
    return veiculo