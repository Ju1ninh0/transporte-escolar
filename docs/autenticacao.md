# Autenticação: Supabase Auth + PostgreSQL

## Princípio
- **Supabase Auth** responde "quem é?": sessão, login, logout e o UUID do usuário (`sub` do token).
- **PostgreSQL local** responde "o que ele é?": `usuarios.auth_user_id` → nome, e-mail, telefone, perfil,
  `empresa_id`, `ativo` e todos os relacionamentos.
- Não existe segunda tabela de usuários como fonte de verdade. O frontend **não** consulta
  `public."Usuarios"` do Supabase.

## Fluxo
```
login  : supabase.auth.signInWithPassword() -> access token -> GET /api/v1/auth/me -> Usuario (PostgreSQL)
inicial: INITIAL_SESSION -> sessão Supabase -> GET /api/v1/auth/me -> setUser(usuario)
logout : supabase.auth.signOut({ scope: "local" })
```
O FastAPI valida o token (assinatura via JWKS `/auth/v1/.well-known/jwks.json` ou HS256 legado,
`iss`, `aud=authenticated`, `exp`, `sub` UUID) e procura `Usuario.auth_user_id == sub`.
Nada enviado pelo cliente (e-mail, perfil, usuario_id, metadata) decide a identidade.

## Respostas de erro (`detail = {code, message}`)
| HTTP | code | Significado |
|---|---|---|
| 401 | `nao_autenticado` / `token_invalido` / `token_expirado` | sem token, token ruim ou sessão expirada |
| 403 | `usuario_nao_cadastrado` | token válido, mas nenhum `usuarios.auth_user_id` com esse UUID |
| 403 | `usuario_inativo` | cadastro existe mas `ativo = false` |
| 403 | `sem_permissao` | autenticado, perfil sem acesso ao recurso |
| 503 | `auth_indisponivel` / `auth_nao_configurada` | JWKS inacessível ou `SUPABASE_URL`/segredo ausente no backend |

## Vincular um usuário que já existe (migração inicial, manual e auditada)
O backend **não** vincula por e-mail automaticamente. Pegue o *User UID* em Supabase → Authentication → Users:
```powershell
docker compose exec backend python -m app.scripts.vincular_auth_user listar
docker compose exec backend python -m app.scripts.vincular_auth_user vincular --email admin@demo.com --auth-user-id <UUID> --dry-run
docker compose exec backend python -m app.scripts.vincular_auth_user vincular --email admin@demo.com --auth-user-id <UUID>
```
Nunca apaga usuários; recusa UUID que já pertence a outro cadastro; troca de UUID só com `--substituir`.

## Variáveis
- Backend/Docker (`.env`, fora do git): `SUPABASE_URL` (obrigatória) e `SUPABASE_JWT_SECRET` (só se o
  projeto ainda usar HS256). Depois de editar o `.env`: `docker compose up -d --force-recreate backend`
  (`restart` não relê o `env_file`).
- Frontend: apenas `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL` e a *publishable key*.
  A service role key nunca vai para o frontend nem para `NEXT_PUBLIC_*`.

## Diagnóstico rápido
```powershell
docker compose exec backend printenv SUPABASE_URL
curl https://<projeto>.supabase.co/auth/v1/.well-known/jwks.json   # keys com "alg":"ES256" => nada de segredo; keys vazio => HS256, configure SUPABASE_JWT_SECRET
docker compose logs backend --tail 50                              # mostra o motivo exato e o sub do token
```

## Próximo passo (criação automática de MOTORISTA/RESPONSAVEL)
Criar o usuário no Supabase Auth (Admin API, com a service role **só no backend**) com senha temporária,
gravar `usuarios.auth_user_id` com o UUID retornado na mesma operação, e tornar `usuarios.senha_hash`
opcional (hoje é NOT NULL e só serve ao login legado).
