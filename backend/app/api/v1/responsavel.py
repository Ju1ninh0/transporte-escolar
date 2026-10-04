from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models import (
    Aluno,
    Configuracao,
    HistoricoRota,
    Mensalidade,
    Motorista,
    Notificacao,
    Ocorrencia,
    Parada,
    Perfil,
    PresencaViagem,
    Responsavel,
    Rota,
    RotaAluno,
    StatusMensalidade,
    StatusRota,
    TipoOcorrencia,
    Usuario,
    Veiculo,
)
from app.models.mixins import agora
from app.schemas.financeiro import MensalidadeDetalhe, MensalidadeOut
from app.schemas.gps import ViagemAtivaOut
from app.schemas.responsavel import (
    AcompanhamentoOut,
    AvisoOut,
    FilhoOut,
    OcorrenciaFilhoOut,
    PixOut,
    PresencaHistoricoOut,
    ResumoAvisos,
)
from app.services.alunos import alunos_visiveis
from app.services.financeiro import (
    ZERO,
    get_mensalidade_ou_none,
    hoje,
    query_base,
    to_detalhe,
    to_out,
    total_pago,
    totais_pagos,
)
from app.services.gps import rotas_visiveis, viagens_ativas
from app.services.viagem import viagens_em_andamento

router = APIRouter(prefix="/responsavel", tags=["responsavel"])
responsavel_only = require_role(Perfil.RESPONSAVEL)


# ------------------------------------------------------------------ helpers
def _responsavel(db: Session, user: Usuario) -> Responsavel:
    r = db.scalar(select(Responsavel).where(Responsavel.usuario_id == user.id))
    if r is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cadastro de responsável não encontrado")
    return r


def _filhos(db: Session, user: Usuario) -> list[Aluno]:
    return list(db.scalars(alunos_visiveis(user).where(Aluno.ativo.is_(True)).order_by(Aluno.nome)).all())


def _filho(db: Session, user: Usuario, aluno_id: int) -> Aluno:
    aluno = db.scalars(alunos_visiveis(user).where(Aluno.id == aluno_id)).first()
    if aluno is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aluno não encontrado")
    return aluno


# ------------------------------------------------------------------- filhos
@router.get("/filhos", response_model=list[FilhoOut])
def meus_filhos(db: Session = Depends(get_db), user: Usuario = Depends(responsavel_only)):
    filhos = _filhos(db, user)
    if not filhos:
        return []
    ids = [f.id for f in filhos]
    vinculos = db.execute(
        select(RotaAluno.aluno_id, Rota.id, Rota.nome, RotaAluno.parada_id, Parada.nome)
        .join(Rota, Rota.id == RotaAluno.rota_id)
        .outerjoin(Parada, Parada.id == RotaAluno.parada_id)
        .where(RotaAluno.aluno_id.in_(ids), Rota.status == StatusRota.ATIVA)
        .order_by(Rota.nome)
    ).all()
    ativas = viagens_em_andamento(db, list({v[1] for v in vinculos}))
    por_aluno: dict[int, list[dict]] = {}
    for aluno_id, rota_id, rota_nome, parada_id, parada_nome in vinculos:
        por_aluno.setdefault(aluno_id, []).append(
            {
                "rota_id": rota_id,
                "rota_nome": rota_nome,
                "parada_id": parada_id,
                "parada_nome": parada_nome,
                "viagem_em_andamento_id": ativas.get(rota_id),
            }
        )
    return [
        {
            "id": f.id,
            "nome": f.nome,
            "escola": f.escola,
            "serie": f.serie,
            "rotas": por_aluno.get(f.id, []),
        }
        for f in filhos
    ]


@router.get("/filhos/{aluno_id}/acompanhamento", response_model=AcompanhamentoOut)
def acompanhamento(
    aluno_id: int, db: Session = Depends(get_db), user: Usuario = Depends(responsavel_only)
):
    aluno = _filho(db, user, aluno_id)
    vinculos = db.execute(
        select(Rota, RotaAluno.parada_id, Parada.nome, Veiculo.apelido, Veiculo.placa, Usuario.nome)
        .select_from(RotaAluno)
        .join(Rota, Rota.id == RotaAluno.rota_id)
        .outerjoin(Parada, Parada.id == RotaAluno.parada_id)
        .outerjoin(Veiculo, Veiculo.id == Rota.veiculo_id)
        .outerjoin(Motorista, Motorista.id == Rota.motorista_id)
        .outerjoin(Usuario, Usuario.id == Motorista.usuario_id)
        .where(RotaAluno.aluno_id == aluno.id, Rota.status == StatusRota.ATIVA)
        .order_by(Rota.nome)
    ).all()
    rota_ids = [v[0].id for v in vinculos]

    paradas: dict[int, list[Parada]] = {}
    if rota_ids:
        for p in db.scalars(
            select(Parada).where(Parada.rota_id.in_(rota_ids)).order_by(Parada.rota_id, Parada.ordem)
        ).all():
            paradas.setdefault(p.rota_id, []).append(p)

    ativas = {v["rota_id"]: v for v in viagens_ativas(db, user.empresa_id, set(rota_ids))}
    chamada: dict[int, object] = {}
    if ativas:
        linhas = db.execute(
            select(PresencaViagem.historico_rota_id, PresencaViagem.status).where(
                PresencaViagem.aluno_id == aluno.id,
                PresencaViagem.historico_rota_id.in_([v["viagem_id"] for v in ativas.values()]),
            )
        ).all()
        chamada = {viagem_id: st for viagem_id, st in linhas}

    rotas = []
    for rota, parada_id, parada_nome, apelido, placa, motorista in vinculos:
        v = ativas.get(rota.id)
        rotas.append(
            {
                "rota_id": rota.id,
                "rota_nome": rota.nome,
                "escola": rota.escola,
                "veiculo_apelido": apelido,
                "veiculo_placa": placa,
                "motorista_nome": motorista,
                "parada_id": parada_id,
                "parada_nome": parada_nome,
                "paradas": [
                    {
                        "id": p.id,
                        "rota_id": p.rota_id,
                        "nome": p.nome,
                        "latitude": p.latitude,
                        "longitude": p.longitude,
                        "ordem": p.ordem,
                    }
                    for p in paradas.get(rota.id, [])
                ],
                "viagem": (
                    {
                        "viagem_id": v["viagem_id"],
                        "iniciada_em": v["iniciada_em"],
                        "motorista_nome": v["motorista_nome"],
                        "posicao": v["posicao"],
                        "status_chamada": chamada.get(v["viagem_id"]),
                    }
                    if v
                    else None
                ),
            }
        )
    return {"aluno_id": aluno.id, "aluno_nome": aluno.nome, "rotas": rotas}


@router.get("/viagens/ativas", response_model=list[ViagemAtivaOut])
def viagens_dos_meus_filhos(
    db: Session = Depends(get_db), user: Usuario = Depends(responsavel_only)
):
    return viagens_ativas(db, user.empresa_id, rotas_visiveis(db, user))


@router.get("/filhos/{aluno_id}/presencas", response_model=PresencaHistoricoOut)
def historico_presencas(
    aluno_id: int,
    dias: int = Query(default=30, ge=1, le=366),
    db: Session = Depends(get_db),
    user: Usuario = Depends(responsavel_only),
):
    aluno = _filho(db, user, aluno_id)
    desde = agora() - timedelta(days=dias)
    linhas = db.execute(
        select(PresencaViagem, HistoricoRota.iniciada_em, Rota.nome)
        .join(HistoricoRota, HistoricoRota.id == PresencaViagem.historico_rota_id)
        .join(Rota, Rota.id == HistoricoRota.rota_id)
        .where(PresencaViagem.aluno_id == aluno.id, HistoricoRota.iniciada_em >= desde)
        .order_by(HistoricoRota.iniciada_em.desc(), PresencaViagem.id.desc())
    ).all()
    registros = [
        {
            "viagem_id": p.historico_rota_id,
            "iniciada_em": iniciada_em,
            "rota_nome": rota_nome,
            "status": p.status,
            "observacao": p.observacao,
        }
        for p, iniciada_em, rota_nome in linhas
    ]
    return {
        "aluno_id": aluno.id,
        "aluno_nome": aluno.nome,
        "dias": dias,
        "presentes": sum(1 for r in registros if r["status"].value == "PRESENTE"),
        "faltas": sum(1 for r in registros if r["status"].value == "FALTA"),
        "registros": registros,
    }


# --------------------------------------------------------------- financeiro
@router.get("/mensalidades", response_model=list[MensalidadeOut])
def minhas_mensalidades(
    status_: StatusMensalidade | None = Query(default=None, alias="status"),
    aluno_id: int | None = None,
    db: Session = Depends(get_db),
    user: Usuario = Depends(responsavel_only),
):
    resp = _responsavel(db, user)
    if aluno_id is not None:
        _filho(db, user, aluno_id)
    ref = hoje()
    q = query_base(user.empresa_id).where(Mensalidade.responsavel_id == resp.id)
    if aluno_id is not None:
        q = q.where(Mensalidade.aluno_id == aluno_id)
    rows = db.execute(q.order_by(Mensalidade.vencimento.desc(), Mensalidade.id.desc())).all()
    pagos = totais_pagos(db, [m.id for m, _, _ in rows])
    itens = [to_out(m, an, rn, pagos.get(m.id, ZERO), ref) for m, an, rn in rows]
    if status_ is not None:
        itens = [i for i in itens if i.status == status_]
    return itens


@router.get("/mensalidades/{mensalidade_id}", response_model=MensalidadeDetalhe)
def minha_mensalidade(
    mensalidade_id: int, db: Session = Depends(get_db), user: Usuario = Depends(responsavel_only)
):
    resp = _responsavel(db, user)
    row = get_mensalidade_ou_none(db, user.empresa_id, mensalidade_id)
    if row is None or row[0].responsavel_id != resp.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mensalidade não encontrada")
    m, an, rn = row
    return to_detalhe(db, m, an, rn, total_pago(db, m.id), hoje())


@router.get("/pix", response_model=PixOut | None)
def dados_pix(db: Session = Depends(get_db), user: Usuario = Depends(responsavel_only)):
    cfg = db.scalar(
        select(Configuracao).where(
            Configuracao.empresa_id == user.empresa_id, Configuracao.chave == "pix"
        )
    )
    if cfg is None or not cfg.valor.get("chave"):
        return None
    return {
        "recebedor": cfg.valor.get("recebedor", ""),
        "tipo_chave": cfg.valor.get("tipo_chave", ""),
        "chave": cfg.valor["chave"],
        "mensagem": cfg.valor.get("mensagem") or None,
    }


# --------------------------------------------------------------- ocorrências
@router.get("/ocorrencias", response_model=list[OcorrenciaFilhoOut])
def minhas_ocorrencias(
    aluno_id: int | None = None,
    db: Session = Depends(get_db),
    user: Usuario = Depends(responsavel_only),
):
    if aluno_id is not None:
        _filho(db, user, aluno_id)
    ids = [a.id for a in db.scalars(alunos_visiveis(user)).all()]
    if aluno_id is not None:
        ids = [aluno_id]
    if not ids:
        return []
    linhas = db.execute(
        select(Ocorrencia, Aluno.nome, TipoOcorrencia.nome)
        .join(Aluno, Aluno.id == Ocorrencia.aluno_id)
        .join(TipoOcorrencia, TipoOcorrencia.id == Ocorrencia.tipo_id)
        .where(Ocorrencia.aluno_id.in_(ids))
        .order_by(Ocorrencia.data.desc(), Ocorrencia.id.desc())
    ).all()
    return [
        {
            "id": o.id,
            "aluno_id": o.aluno_id,
            "aluno_nome": aluno_nome,
            "tipo_nome": tipo_nome,
            "data": o.data,
            "gravidade": o.gravidade,
            "descricao": o.descricao,
            "consequencia": o.consequencia,
        }
        for o, aluno_nome, tipo_nome in linhas
    ]


# ------------------------------------------------------------------- avisos
@router.get("/avisos", response_model=list[AvisoOut])
def meus_avisos(
    somente_nao_lidas: bool = False,
    db: Session = Depends(get_db),
    user: Usuario = Depends(responsavel_only),
):
    q = select(Notificacao).where(Notificacao.usuario_id == user.id)
    if somente_nao_lidas:
        q = q.where(Notificacao.lida.is_(False))
    return db.scalars(q.order_by(Notificacao.created_at.desc(), Notificacao.id.desc()).limit(100)).all()


@router.get("/avisos/resumo", response_model=ResumoAvisos)
def resumo_avisos(db: Session = Depends(get_db), user: Usuario = Depends(responsavel_only)):
    total = db.scalar(
        select(func.count(Notificacao.id)).where(
            Notificacao.usuario_id == user.id, Notificacao.lida.is_(False)
        )
    )
    return {"nao_lidas": total or 0}


@router.post("/avisos/lidas", status_code=status.HTTP_204_NO_CONTENT)
def marcar_todas_lidas(db: Session = Depends(get_db), user: Usuario = Depends(responsavel_only)):
    db.execute(
        update(Notificacao)
        .where(Notificacao.usuario_id == user.id, Notificacao.lida.is_(False))
        .values(lida=True)
    )
    db.commit()


@router.post("/avisos/{aviso_id}/lida", status_code=status.HTTP_204_NO_CONTENT)
def marcar_lida(
    aviso_id: int, db: Session = Depends(get_db), user: Usuario = Depends(responsavel_only)
):
    aviso = db.scalar(
        select(Notificacao).where(Notificacao.id == aviso_id, Notificacao.usuario_id == user.id)
    )
    if aviso is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aviso não encontrado")
    aviso.lida = True
    db.commit()