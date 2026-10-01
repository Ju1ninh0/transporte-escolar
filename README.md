# Transporte Escolar
Sistema web/PWA de gestão de transporte escolar. Ver `docs/arquitetura.md`.

## Rodar (fase atual)
    cp .env.example .env        # edite as senhas
    docker compose up --build
    curl localhost:8000/health

## Testes backend
    cd backend && python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt && pytest && ruff check .

## Fases
1 arquitetura/banco/auth/usuários/alunos · 2 frequência/ocorrências/financeiro/PIX · 3 rotas/GPS/mapa/WS · 4 notificações/PWA/relatórios · 5 gateway/IA/nativo

## Banco, seed e API (fase 1B)
    docker compose exec backend alembic revision --autogenerate -m "init"
    docker compose exec backend alembic upgrade head
    docker compose exec backend python -m app.seed
    # docs interativos: http://localhost:8000/docs
    # logins DEV (senha dev-only-123): admin@demo.com, motorista@demo.com, responsavel@demo.com
