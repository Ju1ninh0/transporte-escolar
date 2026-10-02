from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import admin_only
from app.db.session import get_db
from app.models import Aluno, Gravidade, Ocorrencia, RegraReincidencia, TipoOcorrencia, Usuario
from app.schemas.ocorrencia import (
    OcorrenciaCreate, OcorrenciaOut, OcorrenciaUpdate, SugestaoConsequencia,
)

router = APIRouter(prefix="/ocorrencias", tags=["ocorrencias"])

_OBRIGATORIOS = {"tipo_id", "data", "gravidade", "descricao"}


def _base(empresa_id: int):
    # Ocorrencia não tem empresa_id: o escopo vem do Aluno
    return (
        select(Ocorrencia, Aluno.nome, TipoOcorrencia.nome, Usuario.nome)
        .join(Aluno, Aluno.id == Ocorrencia.aluno_id)
        .join(TipoOcorrencia, TipoOcorrencia.id == Ocorrencia.tipo_id)
        .join(Usuario, Usuario.id == Ocorrencia.registrado_por)
        .where(Aluno.empresa_id == empresa_id)
    )


def _out(row) -> OcorrenciaOut:
    oc, aluno_nome, tipo_nome, registrador = row
    return OcorrenciaOut(
        id=oc.id, aluno_id=oc.aluno_id, aluno_nome=aluno_nome,
        tipo_id=oc.tipo_id, tipo_nome=tipo_nome, data=oc.data,
        gravidade=oc.gravidade, descricao=oc.descricao, consequencia=oc.consequencia,
        registrado_por=oc.registrado_por, registrado_por_nome=registrador,
        created_at=oc.created_at,
    )


def _carregar(db: Session, empresa_id: int, ocorrencia_id: int):
    row = db.execute(_base(empresa_id).where(Ocorrencia.id == ocorrencia_id)).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ocorrência não encontrada")
    return row


def _validar_aluno(db: Session, empresa_id: int, aluno_id: int) -> None:
    ok = db.scalar(select(Aluno.id).where(Aluno.id == aluno_id, Aluno.empresa_id == empresa_id))
    if ok is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aluno não encontrado")


def _validar_tipo_ativo(db: Session, empresa_id: int, tipo_id: int) -> None:
    tipo = db.scalar(
        select(TipoOcorrencia).where(
            TipoOcorrencia.id == tipo_id, TipoOcorrencia.empresa_id == empresa_id
        )
    )
    if tipo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tipo de ocorrência não encontrado")
    if not tipo.ativo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tipo de ocorrência inativo")


@router.get("", response_model=list[OcorrenciaOut])
def listar(
    aluno_id: int | None = None,
    tipo_id: int | None = None,
    gravidade: Gravidade | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    q = _base(user.empresa_id)
    if aluno_id is not None:
        q = q.where(Ocorrencia.aluno_id == aluno_id)
    if tipo_id is not None:
        q = q.where(Ocorrencia.tipo_id == tipo_id)
    if gravidade is not None:
        q = q.where(Ocorrencia.gravidade == gravidade)
    if data_inicio is not None:
        q = q.where(Ocorrencia.data >= data_inicio)
    if data_fim is not None:
        q = q.where(Ocorrencia.data <= data_fim)
    q = q.order_by(Ocorrencia.data.desc(), Ocorrencia.id.desc())
    return [_out(r) for r in db.execute(q).all()]


# declarada ANTES de /{ocorrencia_id}, senão "sugestao-consequencia" vira id
@router.get("/sugestao-consequencia", response_model=SugestaoConsequencia)
def sugestao_consequencia(
    aluno_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    _validar_aluno(db, user.empresa_id, aluno_id)
    anteriores = db.scalar(
        select(func.count()).select_from(Ocorrencia).where(Ocorrencia.aluno_id == aluno_id)
    )
    numero = anteriores + 1
    regras = db.scalars(
        select(RegraReincidencia)
        .where(
            RegraReincidencia.empresa_id == user.empresa_id,
            RegraReincidencia.numero_ocorrencia <= numero,
        )
        .order_by(RegraReincidencia.numero_ocorrencia.desc())
    ).all()
    return SugestaoConsequencia(
        aluno_id=aluno_id,
        numero_ocorrencia=numero,
        consequencia=regras[0].consequencia if regras else None,
    )


@router.get("/{ocorrencia_id}", response_model=OcorrenciaOut)
def consultar(
    ocorrencia_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    return _out(_carregar(db, user.empresa_id, ocorrencia_id))


@router.post("", response_model=OcorrenciaOut, status_code=status.HTTP_201_CREATED)
def criar(
    body: OcorrenciaCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    _validar_aluno(db, user.empresa_id, body.aluno_id)
    _validar_tipo_ativo(db, user.empresa_id, body.tipo_id)
    oc = Ocorrencia(**body.model_dump(), registrado_por=user.id)
    db.add(oc)
    db.commit()
    return _out(_carregar(db, user.empresa_id, oc.id))


@router.patch("/{ocorrencia_id}", response_model=OcorrenciaOut)
def atualizar(
    ocorrencia_id: int,
    body: OcorrenciaUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(admin_only),
):
    oc = _carregar(db, user.empresa_id, ocorrencia_id)[0]
    dados = body.model_dump(exclude_unset=True)
    if any(k in _OBRIGATORIOS and v is None for k, v in dados.items()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Campo obrigatório não pode ser nulo")
    if "tipo_id" in dados and dados["tipo_id"] != oc.tipo_id:
        _validar_tipo_ativo(db, user.empresa_id, dados["tipo_id"])
    for k, v in dados.items():
        setattr(oc, k, v)
    db.commit()
    return _out(_carregar(db, user.empresa_id, oc.id))