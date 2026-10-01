# Arquitetura

## Visão geral
Monólito modular (API única) + PWA. Simples de operar agora, separável depois.

    Celular/PC (Next.js PWA) --HTTPS/REST--> FastAPI --SQLAlchemy--> PostgreSQL
                             --WebSocket---> FastAPI (hub em memória)

## Decisões
- **Monólito modular**: um backend FastAPI dividido por domínio. Evita a complexidade de microsserviços.
- **Multi-tenant desde já**: tabelas de negócio com `empresa_id` (futuro SaaS), filtrado na camada de serviço.
- **Auth**: JWT de acesso curto (15 min) + refresh token com rotação, guardado hasheado. Senhas com Argon2.
- **Autorização**: dependência `require_role(...)` + verificação de posse (responsável só vê seus filhos; motorista só suas rotas).
- **Migrations**: Alembic. Nunca `create_all` em produção.
- **GPS**: motorista envia posições por WebSocket autenticado, só com rota ativa. Última posição no hub em memória; `localizacoes` recebe amostras espaçadas. Responsáveis assinam por rota. Para escalar: Redis pub/sub.
- **Alerta de proximidade**: distância haversine até a parada; raio em `configuracoes` (padrão 500 m).
- **Regras de ocorrência**: tabela `regras_reincidencia` (nº da ocorrência -> consequência), editável pelo admin.
- **PIX**: interface `PagamentoProvider`; implementação inicial `PixManual` (chave + BR Code). Gateway entra depois sem mudar as rotas.
- **Notificações**: tabela interna + interface `Notifier`; Web Push depois.
- **LGPD**: minimização de dados, auditoria, retenção configurável, anonimização. Pontos jurídicos devem ser validados por profissional.

## Estrutura do backend
    app/core      config, segurança (hash, JWT)
    app/db        sessão, Base
    app/models    entidades SQLAlchemy
    app/schemas   Pydantic
    app/api/v1    routers por domínio
    app/services  regras de negócio
    app/ws        hub WebSocket de GPS
