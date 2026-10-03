from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import admin_only
from app.db.session import get_db
from app.models import Motorista, Parada, Rota, RotaAluno, StatusRota, Usuario, Veiculo
from app.schemas.frota import RotaCreate, RotaDetalheOut, RotaOut, RotaUpdate
from app.services.frota import (
    alunos_da_rota,
    obter_rota,
    total_alunos,
    viagem_em_andamento,
)

router = APIRouter(prefix="/rotas", tags=["rotas"])


def _validar_veiculo(db: Session, empresa_id: int, veiculo_id: int) -> Veiculo:
    veiculo = db.scalar(
        select(Veiculo).where(Veiculo.id == veiculo_id, Veiculo.empresa_id == empresa_id)
    )
    if veiculo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Veículo não encontrado")
    if not veiculo.ativo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Veículo inativo")
    return veiculo


def _validar_motorista(db: Session, empresa_id: int, motorista_id: int) -> Motorista:
    motorista = db.scalar(
        select(Motorista).where(Motorista.id == motorista_id, Motorista.empresa_id == empresa_id)
    )
    if motorista is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Motorista não encontrado")
    return motorista


def _serializar(db: Session, rotas: list[Rota]) -> list[dict]:
    if not rotas:
        return []
    ids = [r.id for r in rotas]

    paradas = {
        rota_id: n
        for rota_id, n in db.execute(
            select(Parada.rota_id, func.count(Parada.id))
            .where(Parada.rota_id.in_(ids))
            .group_by(Parada.rota_id)
        ).all()
    }
    alunos = {
        rota_id: n
        for rota_id, n in db.execute(
            select(RotaAluno.rota_id, func.count(RotaAluno.id))
            .where(RotaAluno.rota_id.in_(ids))
            .group_by(RotaAluno.rota_id)
        ).all()
    }

    veiculo_ids = {r.veiculo_id for r in rotas if r.veiculo_id is not None}
    veiculos = {}
    if veiculo_ids:
        veiculos = {
            v.id: v for v in db.scalars(select(Veiculo).where(Veiculo.id.in_(veiculo_ids))).all()
        }

    motorista_ids = {r.motorista_id for r in rotas if r.motorista_id is not None}
    motoristas = {}
    if motorista_ids:
        motoristas = {
            m_id: nome
            for m_id, nome in db.execute(
                select(Motorista.id, Usuario.nome)
                .join(Usuario, Usuario.id == Motorista.usuario_id)
                .where(Motorista.id.in_(motorista_ids))
            ).all()
        }

    saida = []
    for r in rotas:
        v = veiculos.get(r.veiculo_id)
        saida.append(
            {
                "id": r.id,
                "nome": r.nome,
                "escola": r.escola,
                "status": r.status,
                "veiculo": {"id": v.id, "placa": v.placa, "apelido": v.apelido} if v else None,
                "motorista": (
                    {"id": r.motorista_id, "nome": motoristas[r.motorista_id]}
                    if r.motorista_id in motoristas
                    else None
                ),
                "total_paradas": paradas.get(r.id, 0),
                "total_alunos": alunos.get(r.id, 0),
            }
        )
    return saida


@router.get("", response_model=list[RotaOut])
def listar(
    status_filtro: StatusRota | None = Query(default=None, alias="status"),
    motorista_id: int | None = None,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    q = select(Rota).where(Rota.empresa_id == user.empresa_id)
    if status_filtro is not None:
        q = q.where(Rota.status == status_filtro)
    if motorista_id is not None:
        q = q.where(Rota.motorista_id == motorista_id)
    rotas = db.scalars(q.order_by(Rota.nome)).all()
    return _serializar(db, list(rotas))


@router.get("/{rota_id}", response_model=RotaDetalheOut)
def detalhar(rota_id: int, db: Session = Depends(get_db), user: Usuario = Depends(admin_only)):
    rota = obter_rota(db, user.empresa_id, rota_id)
    dados = _serializar(db, [rota])[0]
    paradas = db.scalars(
        select(Parada).where(Parada.rota_id == rota.id).order_by(Parada.ordem)
    ).all()
    dados["paradas"] = [
        {
            "id": p.id,
            "rota_id": p.rota_id,
            "nome": p.nome,
            "latitude": p.latitude,
            "longitude": p.longitude,
            "ordem": p.ordem,
        }
        for p in paradas
    ]
    dados["alunos"] = alunos_da_rota(db, rota.id)
    return dados


@router.post("", response_model=RotaOut, status_code=status.HTTP_201_CREATED)
def criar(body: RotaCreate, db: Session = Depends(get_db), user: Usuario = Depends(admin_only)):
    if body.veiculo_id is not None:
        _validar_veiculo(db, user.empresa_id, body.veiculo_id)
    if body.motorista_id is not None:
        _validar_motorista(db, user.empresa_id, body.motorista_id)
    rota = Rota(
        empresa_id=user.empresa_id,
        nome=body.nome,
        escola=body.escola,
        veiculo_id=body.veiculo_id,
        motorista_id=body.motorista_id,
        status=body.status,
    )
    db.add(rota)
    db.commit()
    db.refresh(rota)
    return _serializar(db, [rota])[0]


@router.patch("/{rota_id}", response_model=RotaOut)
def atualizar(
    rota_id: int,
    body: RotaUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    rota = obter_rota(db, user.empresa_id, rota_id)
    dados = body.model_dump(exclude_unset=True)
    # nome e status não podem ser nulos; veiculo_id/motorista_id/escola aceitam null
    for campo in ("nome", "status"):
        if dados.get(campo) is None:
            dados.pop(campo, None)

    novo_veiculo = dados.get("veiculo_id")
    if novo_veiculo is not None and novo_veiculo != rota.veiculo_id:
        veiculo = _validar_veiculo(db, user.empresa_id, novo_veiculo)
        if total_alunos(db, rota.id) > veiculo.capacidade:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Capacidade do veículo é menor que o total de alunos da rota",
            )

    novo_motorista = dados.get("motorista_id")
    if novo_motorista is not None and novo_motorista != rota.motorista_id:
        _validar_motorista(db, user.empresa_id, novo_motorista)

    if (
        dados.get("status") == StatusRota.INATIVA
        and rota.status != StatusRota.INATIVA
        and viagem_em_andamento(db, rota.id)
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Não é possível inativar uma rota com viagem em andamento"
        )

    for k, v in dados.items():
        setattr(rota, k, v)
    db.commit()
    db.refresh(rota)
    return _serializar(db, [rota])[0]