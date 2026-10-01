from sqlalchemy import Select, select

from app.models import Aluno, Motorista, Perfil, Responsavel, Rota, RotaAluno, Usuario


def alunos_visiveis(user: Usuario) -> Select:
    q = select(Aluno).where(Aluno.empresa_id == user.empresa_id)
    if user.perfil == Perfil.RESPONSAVEL:
        q = q.join(Responsavel, Responsavel.id == Aluno.responsavel_id).where(
            Responsavel.usuario_id == user.id
        )
    elif user.perfil == Perfil.MOTORISTA:
        q = (
            q.join(RotaAluno, RotaAluno.aluno_id == Aluno.id)
            .join(Rota, Rota.id == RotaAluno.rota_id)
            .join(Motorista, Motorista.id == Rota.motorista_id)
            .where(Motorista.usuario_id == user.id)
            .distinct()
        )
    return q
