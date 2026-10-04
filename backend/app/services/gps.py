from dataclasses import dataclass

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Aluno,
    HistoricoRota,
    Localizacao,
    Motorista,
    Perfil,
    Responsavel,
    Rota,
    RotaAluno,
    StatusExecucao,
    Usuario,
    Veiculo,
)


@dataclass(eq=False)
class Assinante:
    ws: object
    empresa_id: int
    rotas: set[int] | None  # None = todas as rotas da empresa (admin)


class Hub:
    """Distribui eventos de GPS para quem está conectado (em memória, um processo)."""

    def __init__(self) -> None:
        self._assinantes: set[Assinante] = set()

    def total(self) -> int:
        return len(self._assinantes)

    def adicionar(self, assinante: Assinante) -> None:
        self._assinantes.add(assinante)

    def remover(self, assinante: Assinante) -> None:
        self._assinantes.discard(assinante)

    async def publicar(self, evento: dict, empresa_id: int, rota_id: int) -> None:
        dados = jsonable_encoder(evento)
        for a in list(self._assinantes):
            if a.empresa_id != empresa_id:
                continue
            if a.rotas is not None and rota_id not in a.rotas:
                continue
            try:
                await a.ws.send_json(dados)  # type: ignore[attr-defined]
            except Exception:
                self._assinantes.discard(a)


hub = Hub()


def rotas_visiveis(db: Session, user: Usuario) -> set[int] | None:
    """None = todas as rotas da empresa (admin). Responsável: só rotas onde há filho dele."""
    if user.perfil == Perfil.ADMIN:
        return None
    ids = db.scalars(
        select(RotaAluno.rota_id)
        .join(Aluno, Aluno.id == RotaAluno.aluno_id)
        .join(Responsavel, Responsavel.id == Aluno.responsavel_id)
        .where(
            Responsavel.usuario_id == user.id,
            Aluno.empresa_id == user.empresa_id,
            Aluno.ativo.is_(True),
        )
        .distinct()
    ).all()
    return set(ids)


def posicao_dict(loc: Localizacao) -> dict:
    return {
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "velocidade": loc.velocidade,
        "direcao": loc.direcao,
        "timestamp": loc.timestamp,
    }


def viagens_ativas(db: Session, empresa_id: int, rotas: set[int] | None) -> list[dict]:
    q = (
        select(HistoricoRota, Rota.nome, Veiculo.apelido, Veiculo.placa, Usuario.nome)
        .join(Rota, Rota.id == HistoricoRota.rota_id)
        .outerjoin(Veiculo, Veiculo.id == HistoricoRota.veiculo_id)
        .outerjoin(Motorista, Motorista.id == HistoricoRota.motorista_id)
        .outerjoin(Usuario, Usuario.id == Motorista.usuario_id)
        .where(Rota.empresa_id == empresa_id, HistoricoRota.status == StatusExecucao.EM_ANDAMENTO)
    )
    if rotas is not None:
        if not rotas:
            return []
        q = q.where(Rota.id.in_(rotas))
    linhas = db.execute(q.order_by(HistoricoRota.iniciada_em, HistoricoRota.id)).all()
    if not linhas:
        return []

    ids = [v.id for v, *_ in linhas]
    ultimas_ids = (
        select(func.max(Localizacao.id))
        .where(Localizacao.historico_rota_id.in_(ids))
        .group_by(Localizacao.historico_rota_id)
    )
    ultimas = {
        loc.historico_rota_id: loc
        for loc in db.scalars(select(Localizacao).where(Localizacao.id.in_(ultimas_ids))).all()
    }
    return [
        {
            "viagem_id": v.id,
            "rota_id": v.rota_id,
            "rota_nome": rota_nome,
            "veiculo_apelido": apelido,
            "veiculo_placa": placa,
            "motorista_nome": motorista_nome,
            "iniciada_em": v.iniciada_em,
            "posicao": posicao_dict(ultimas[v.id]) if v.id in ultimas else None,
        }
        for v, rota_nome, apelido, placa, motorista_nome in linhas
    ]