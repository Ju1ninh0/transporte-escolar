from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import admin_only, get_db
from app.models import Aluno, Mensalidade, Pagamento, StatusMensalidade, Usuario
from app.schemas.financeiro import (MensalidadeCreate, MensalidadeDetalhe,
                                    MensalidadeOut, MensalidadeUpdate,
                                    PagamentoCreate, ResumoFinanceiro)
from app.services.financeiro import (PAGAMENTO_CONFIRMADO, ZERO,
                                     get_mensalidade_ou_none, hoje, query_base,
                                     saldo_mensalidade, sincronizar_status,
                                     status_efetivo, to_detalhe, to_out,
                                     total_pago, totais_pagos)

router = APIRouter(prefix="/financeiro", tags=["financeiro"])


def _nao_encontrada() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Mensalidade não encontrada")


@router.get("/resumo", response_model=ResumoFinanceiro)
def resumo(db: Session = Depends(get_db), admin: Usuario = Depends(admin_only)):
    ref = hoje()
    rows = db.execute(
        query_base(admin.empresa_id).where(Mensalidade.mes_referencia == ref.replace(day=1))
    ).all()
    pagos = totais_pagos(db, [m.id for m, _, _ in rows])
    r = {"total_previsto": ZERO, "total_recebido": ZERO,
         "total_pendente": ZERO, "total_atrasado": ZERO}
    for m, _, _ in rows:
        pago = pagos.get(m.id, ZERO)
        st = status_efetivo(m, pago, ref)
        if st == StatusMensalidade.CANCELADO:
            continue
        r["total_previsto"] += m.valor
        r["total_recebido"] += pago
        if st == StatusMensalidade.PENDENTE:
            r["total_pendente"] += saldo_mensalidade(m, pago)
        elif st == StatusMensalidade.ATRASADO:
            r["total_atrasado"] += saldo_mensalidade(m, pago)
    return r


@router.get("/mensalidades", response_model=list[MensalidadeOut])
def listar(status_: StatusMensalidade | None = Query(default=None, alias="status"),
           aluno_id: int | None = None,
           mes_referencia: date | None = None,
           db: Session = Depends(get_db), admin: Usuario = Depends(admin_only)):
    ref = hoje()
    q = query_base(admin.empresa_id)
    if aluno_id is not None:
        q = q.where(Mensalidade.aluno_id == aluno_id)
    if mes_referencia is not None:
        q = q.where(Mensalidade.mes_referencia == mes_referencia.replace(day=1))
    rows = db.execute(q.order_by(Mensalidade.vencimento.desc(), Mensalidade.id.desc())).all()
    pagos = totais_pagos(db, [m.id for m, _, _ in rows])
    itens = [to_out(m, an, rn, pagos.get(m.id, ZERO), ref) for m, an, rn in rows]
    if status_ is not None:
        itens = [i for i in itens if i.status == status_]
    return itens


@router.post("/mensalidades", response_model=MensalidadeOut,
             status_code=status.HTTP_201_CREATED)
def criar(data: MensalidadeCreate, db: Session = Depends(get_db),
          admin: Usuario = Depends(admin_only)):
    aluno = db.scalar(select(Aluno).where(Aluno.id == data.aluno_id,
                                          Aluno.empresa_id == admin.empresa_id))
    if aluno is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aluno não encontrado")
    if not aluno.ativo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Aluno inativo")
    duplicada = db.scalar(select(Mensalidade.id).where(
        Mensalidade.empresa_id == admin.empresa_id,
        Mensalidade.aluno_id == aluno.id,
        Mensalidade.mes_referencia == data.mes_referencia))
    if duplicada:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Já existe mensalidade deste aluno nesta competência")
    nova = Mensalidade(empresa_id=admin.empresa_id, aluno_id=aluno.id,
                       responsavel_id=aluno.responsavel_id, valor=data.valor,
                       mes_referencia=data.mes_referencia, vencimento=data.vencimento,
                       status=StatusMensalidade.PENDENTE)
    db.add(nova)
    db.commit()
    m, an, rn = get_mensalidade_ou_none(db, admin.empresa_id, nova.id)
    return to_out(m, an, rn, ZERO, hoje())


@router.get("/mensalidades/{mensalidade_id}", response_model=MensalidadeDetalhe)
def detalhe(mensalidade_id: int, db: Session = Depends(get_db),
            admin: Usuario = Depends(admin_only)):
    row = get_mensalidade_ou_none(db, admin.empresa_id, mensalidade_id)
    if row is None:
        raise _nao_encontrada()
    m, an, rn = row
    return to_detalhe(db, m, an, rn, total_pago(db, m.id), hoje())


@router.patch("/mensalidades/{mensalidade_id}", response_model=MensalidadeOut)
def atualizar(mensalidade_id: int, data: MensalidadeUpdate,
              db: Session = Depends(get_db), admin: Usuario = Depends(admin_only)):
    row = get_mensalidade_ou_none(db, admin.empresa_id, mensalidade_id, for_update=True)
    if row is None:
        raise _nao_encontrada()
    m, an, rn = row
    campos = data.model_dump(exclude_unset=True)
    pago = total_pago(db, m.id)

    novo_status = campos.pop("status", None)
    if novo_status == StatusMensalidade.PAGO:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "PAGO é definido automaticamente ao quitar a mensalidade")
    if novo_status == StatusMensalidade.ATRASADO:
        novo_status = StatusMensalidade.PENDENTE
    if campos.get("valor") is not None and campos["valor"] < pago:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Valor menor que o total já pago")

    for k, v in campos.items():
        if v is not None:
            setattr(m, k, v)
    if novo_status is not None:
        m.status = novo_status
    sincronizar_status(m, pago)
    db.commit()
    db.refresh(m)
    return to_out(m, an, rn, pago, hoje())


@router.post("/mensalidades/{mensalidade_id}/pagamentos",
             response_model=MensalidadeDetalhe, status_code=status.HTTP_201_CREATED)
def registrar_pagamento(mensalidade_id: int, data: PagamentoCreate,
                        db: Session = Depends(get_db),
                        admin: Usuario = Depends(admin_only)):
    row = get_mensalidade_ou_none(db, admin.empresa_id, mensalidade_id, for_update=True)
    if row is None:
        raise _nao_encontrada()
    m, an, rn = row
    if data.valor <= Decimal("0"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "O valor deve ser maior que zero")
    if m.status == StatusMensalidade.CANCELADO:
        raise HTTPException(status.HTTP_409_CONFLICT, "Mensalidade cancelada")
    pago = total_pago(db, m.id)
    saldo = saldo_mensalidade(m, pago)
    if saldo == ZERO:
        raise HTTPException(status.HTTP_409_CONFLICT, "Mensalidade já quitada")
    if data.valor > saldo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"Valor excede o saldo da mensalidade (restante: R$ {saldo:.2f})")

    db.add(Pagamento(mensalidade_id=m.id, valor=data.valor,
                     data_pagamento=data.data_pagamento, metodo=data.metodo.value,
                     comprovante=data.comprovante, provider_ref=data.provider_ref,
                     status=PAGAMENTO_CONFIRMADO))
    db.flush()
    pago = total_pago(db, m.id)
    sincronizar_status(m, pago)
    db.commit()
    db.refresh(m)
    return to_detalhe(db, m, an, rn, pago, hoje())