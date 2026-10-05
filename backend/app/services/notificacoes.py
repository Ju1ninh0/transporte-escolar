import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Aluno,
    AvisoProximidade,
    Configuracao,
    Notificacao,
    Parada,
    Responsavel,
    RotaAluno,
    Usuario,
)
from app.services.geo import distancia_metros

logger = logging.getLogger(__name__)

PROXIMIDADE_PADRAO_M = 300


def executar_seguro(db: Session, funcao, *args) -> None:
    """Notificar nunca pode quebrar o fluxo principal (iniciar/encerrar viagem, enviar GPS)."""
    try:
        funcao(db, *args)
    except Exception:
        logger.exception("Falha ao gerar notificações")
        db.rollback()


def _destinatarios(db: Session, rota_id: int) -> list[tuple[int, int | None, str]]:
    """(usuario_id do responsável, parada do aluno, nome do aluno) para cada aluno ativo da rota."""
    linhas = db.execute(
        select(Usuario.id, RotaAluno.parada_id, Aluno.nome)
        .select_from(RotaAluno)
        .join(Aluno, Aluno.id == RotaAluno.aluno_id)
        .join(Responsavel, Responsavel.id == Aluno.responsavel_id)
        .join(Usuario, Usuario.id == Responsavel.usuario_id)
        .where(RotaAluno.rota_id == rota_id, Aluno.ativo.is_(True), Usuario.ativo.is_(True))
    ).all()
    return [(u, p, n) for u, p, n in linhas]


def _por_usuario(linhas) -> dict[int, list[str]]:
    saida: dict[int, set[str]] = {}
    for usuario_id, nome in linhas:
        saida.setdefault(usuario_id, set()).add(nome)
    return {u: sorted(nomes) for u, nomes in saida.items()}


def _criar(db: Session, usuario_id: int, tipo: str, titulo: str, mensagem: str) -> None:
    db.add(Notificacao(usuario_id=usuario_id, tipo=tipo, titulo=titulo, mensagem=mensagem))


def notificar_inicio(db: Session, viagem_id: int, rota_id: int, rota_nome: str) -> None:
    por_usuario = _por_usuario((u, n) for u, _, n in _destinatarios(db, rota_id))
    for usuario_id, nomes in por_usuario.items():
        _criar(
            db,
            usuario_id,
            "VIAGEM_INICIADA",
            "Viagem iniciada",
            f"A rota {rota_nome} saiu agora. Aluno(s): {', '.join(nomes)}.",
        )
    db.commit()


def notificar_fim(db: Session, rota_id: int, rota_nome: str) -> None:
    por_usuario = _por_usuario((u, n) for u, _, n in _destinatarios(db, rota_id))
    for usuario_id, nomes in por_usuario.items():
        _criar(
            db,
            usuario_id,
            "VIAGEM_ENCERRADA",
            "Viagem encerrada",
            f"A viagem da rota {rota_nome} foi encerrada. Aluno(s): {', '.join(nomes)}.",
        )
    db.commit()


def _metros_configurados(db: Session, empresa_id: int) -> int:
    cfg = db.scalar(
        select(Configuracao).where(
            Configuracao.empresa_id == empresa_id, Configuracao.chave == "proximidade_metros"
        )
    )
    metros = (cfg.valor or {}).get("metros") if cfg else None
    return int(metros) if metros else PROXIMIDADE_PADRAO_M


def notificar_proximidade(
    db: Session,
    viagem_id: int,
    rota_id: int,
    rota_nome: str,
    empresa_id: int,
    latitude: float,
    longitude: float,
) -> None:
    """Avisa os responsáveis de uma parada, uma única vez por viagem, quando a van chega perto dela."""
    limite = _metros_configurados(db, empresa_id)
    paradas = db.scalars(select(Parada).where(Parada.rota_id == rota_id)).all()
    ja_avisadas = set(
        db.scalars(
            select(AvisoProximidade.parada_id).where(AvisoProximidade.historico_rota_id == viagem_id)
        ).all()
    )
    destinatarios = _destinatarios(db, rota_id)
    dados = [(p.id, p.nome, p.latitude, p.longitude) for p in paradas]

    for parada_id, parada_nome, lat, lng in dados:
        if parada_id in ja_avisadas:
            continue
        distancia = distancia_metros(latitude, longitude, lat, lng)
        if distancia > limite:
            continue
        alvos = [(u, n) for u, pid, n in destinatarios if pid == parada_id]
        if not alvos:
            continue
        aproximada = max(10, int(round(distancia / 10.0)) * 10)
        db.add(AvisoProximidade(historico_rota_id=viagem_id, parada_id=parada_id))
        for usuario_id, nomes in _por_usuario(alvos).items():
            _criar(
                db,
                usuario_id,
                "VAN_PROXIMA",
                "Van se aproximando",
                f'A van da rota {rota_nome} está a cerca de {aproximada} m da parada "{parada_nome}" '
                f"({', '.join(nomes)}).",
            )
        try:
            db.commit()
        except IntegrityError:  # outra requisição avisou ao mesmo tempo
            db.rollback()