from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.deps import admin_only
from app.db.session import get_db
from app.models import Parada, RotaAluno, Usuario
from app.schemas.frota import ParadaCreate, ParadaOut, ParadaReordenar, ParadaUpdate
from app.services.frota import bloquear_se_em_viagem, obter_rota

router = APIRouter(prefix="/rotas/{rota_id}/paradas", tags=["paradas"])

_MSG_VIAGEM = "Não é possível alterar paradas de uma rota com viagem em andamento"


def _ordenadas(db: Session, rota_id: int) -> list[Parada]:
    return list(
        db.scalars(select(Parada).where(Parada.rota_id == rota_id).order_by(Parada.ordem)).all()
    )


def _obter_parada(db: Session, rota_id: int, parada_id: int) -> Parada:
    parada = db.scalar(select(Parada).where(Parada.id == parada_id, Parada.rota_id == rota_id))
    if parada is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Parada não encontrada")
    return parada


@router.get("", response_model=list[ParadaOut])
def listar(rota_id: int, db: Session = Depends(get_db), user: Usuario = Depends(admin_only)):
    rota = obter_rota(db, user.empresa_id, rota_id)
    return _ordenadas(db, rota.id)


@router.post("", response_model=ParadaOut, status_code=status.HTTP_201_CREATED)
def criar(
    rota_id: int,
    body: ParadaCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    rota = obter_rota(db, user.empresa_id, rota_id)
    bloquear_se_em_viagem(db, rota.id, _MSG_VIAGEM)
    if body.ordem is None:
        maior = db.scalar(select(func.max(Parada.ordem)).where(Parada.rota_id == rota.id)) or 0
        ordem = maior + 1
    else:
        existe = db.scalar(
            select(Parada.id).where(Parada.rota_id == rota.id, Parada.ordem == body.ordem)
        )
        if existe is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma parada nessa ordem")
        ordem = body.ordem
    parada = Parada(
        rota_id=rota.id,
        nome=body.nome,
        latitude=body.latitude,
        longitude=body.longitude,
        ordem=ordem,
    )
    db.add(parada)
    db.commit()
    db.refresh(parada)
    return parada


# Precisa vir antes de "/{parada_id}" só por clareza; os métodos são diferentes.
@router.put("/ordem", response_model=list[ParadaOut])
def reordenar(
    rota_id: int,
    body: ParadaReordenar,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    rota = obter_rota(db, user.empresa_id, rota_id)
    bloquear_se_em_viagem(db, rota.id, _MSG_VIAGEM)
    atuais = {p.id: p for p in _ordenadas(db, rota.id)}
    if len(body.ids) != len(set(body.ids)) or set(body.ids) != set(atuais):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "A lista deve conter exatamente as paradas da rota, sem repetição",
        )
    # UniqueConstraint(rota_id, ordem): primeiro ordens temporárias negativas...
    for i, parada in enumerate(atuais.values(), start=1):
        parada.ordem = -i
    db.flush()
    # ...depois as ordens finais 1..N
    for posicao, parada_id in enumerate(body.ids, start=1):
        atuais[parada_id].ordem = posicao
    db.commit()
    return _ordenadas(db, rota.id)


@router.patch("/{parada_id}", response_model=ParadaOut)
def atualizar(
    rota_id: int,
    parada_id: int,
    body: ParadaUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    rota = obter_rota(db, user.empresa_id, rota_id)
    bloquear_se_em_viagem(db, rota.id, _MSG_VIAGEM)
    parada = _obter_parada(db, rota.id, parada_id)
    dados = body.model_dump(exclude_unset=True)
    for campo in ("nome", "latitude", "longitude"):
        if dados.get(campo) is None:
            dados.pop(campo, None)
    for k, v in dados.items():
        setattr(parada, k, v)
    db.commit()
    db.refresh(parada)
    return parada


@router.delete("/{parada_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(
    rota_id: int,
    parada_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    rota = obter_rota(db, user.empresa_id, rota_id)
    bloquear_se_em_viagem(db, rota.id, _MSG_VIAGEM)
    parada = _obter_parada(db, rota.id, parada_id)
    # os alunos continuam na rota, apenas sem parada
    db.execute(update(RotaAluno).where(RotaAluno.parada_id == parada.id).values(parada_id=None))
    db.delete(parada)
    db.commit()