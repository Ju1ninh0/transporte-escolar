"""Vínculo administrativo entre um usuário do Supabase Auth e um cadastro do PostgreSQL local.

Identidade (Supabase)  ->  usuarios.auth_user_id (UUID)  ->  dados do sistema (PostgreSQL)

Este é o ÚNICO caminho para vincular um usuário que já existe. A API nunca vincula sozinha por
e-mail: depois do vínculo a autenticação depende só do UUID.

Como obter o UUID: Supabase Dashboard > Authentication > Users > coluna "User UID".

Uso (a partir da raiz do projeto):
  docker compose exec backend python -m app.scripts.vincular_auth_user listar
  docker compose exec backend python -m app.scripts.vincular_auth_user vincular \\
      --email admin@demo.com --auth-user-id 00000000-0000-0000-0000-000000000000 --dry-run
  docker compose exec backend python -m app.scripts.vincular_auth_user vincular \\
      --email admin@demo.com --auth-user-id 00000000-0000-0000-0000-000000000000

Nunca apaga usuários; só preenche `auth_user_id`.
"""
import argparse
import sys
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Usuario


class ErroVinculo(Exception):
    pass


def normalizar_uuid(valor: str) -> str:
    try:
        return str(uuid.UUID(valor.strip()))
    except ValueError:
        raise ErroVinculo(f"'{valor}' não é um UUID válido.") from None


def vincular(
    db: Session, email: str, auth_user_id: str, *, substituir: bool = False, dry_run: bool = False
) -> str:
    """Vincula e devolve uma mensagem. Não faz commit se dry_run."""
    auth_id = normalizar_uuid(auth_user_id)
    email = email.strip().lower()

    user = db.scalar(select(Usuario).where(Usuario.email == email))
    if user is None:
        raise ErroVinculo(f"Não existe usuário com o e-mail {email} no PostgreSQL local.")

    dono = db.scalar(select(Usuario).where(Usuario.auth_user_id == auth_id))
    if dono is not None and dono.id != user.id:
        raise ErroVinculo(
            f"Esse UUID já pertence a outro cadastro ({dono.email}). Nada foi alterado."
        )
    if user.auth_user_id == auth_id:
        return f"{email} já está vinculado a {auth_id}. Nada a fazer."
    if user.auth_user_id and not substituir:
        raise ErroVinculo(
            f"{email} já está vinculado a outro UUID ({user.auth_user_id}). "
            "Use --substituir se tiver certeza."
        )

    aviso = "" if user.ativo else " ATENÇÃO: o cadastro está inativo e continuará bloqueado."
    if dry_run:
        return f"[dry-run] vincularia {email} ({user.perfil.value}) a {auth_id}.{aviso}"

    user.auth_user_id = auth_id
    db.add(
        AuditLog(
            usuario_id=user.id, acao="vincular_auth_user_id", entidade="usuarios", entidade_id=user.id
        )
    )
    db.commit()
    return f"{email} ({user.perfil.value}) vinculado a {auth_id}.{aviso}"


def listar(db: Session) -> list[str]:
    linhas = [f"{'id':>4}  {'perfil':<12} {'ativo':<5} {'auth_user_id':<36}  email"]
    for u in db.scalars(select(Usuario).order_by(Usuario.id)):
        linhas.append(
            f"{u.id:>4}  {u.perfil.value:<12} {'sim' if u.ativo else 'não':<5} "
            f"{u.auth_user_id or '(sem vínculo)':<36}  {u.email}"
        )
    return linhas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("listar", help="mostra os usuários e se já têm vínculo com o Supabase")
    p = sub.add_parser("vincular", help="vincula um usuário existente a um UUID do Supabase")
    p.add_argument("--email", required=True, help="e-mail do cadastro no PostgreSQL local")
    p.add_argument("--auth-user-id", required=True, help="User UID do Supabase Auth")
    p.add_argument("--substituir", action="store_true", help="permite trocar um UUID já vinculado")
    p.add_argument("--dry-run", action="store_true", help="só mostra o que faria")
    args = parser.parse_args(argv)

    from app.db.session import SessionLocal  # import tardio: só precisa do banco ao executar

    with SessionLocal() as db:
        if args.comando == "listar":
            print("\n".join(listar(db)))
            return 0
        try:
            print(
                vincular(
                    db, args.email, args.auth_user_id,
                    substituir=args.substituir, dry_run=args.dry_run,
                )
            )
        except ErroVinculo as erro:
            print(f"ERRO: {erro}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())