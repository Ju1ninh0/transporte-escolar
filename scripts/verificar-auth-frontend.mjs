// Garante, sem rede e sem banco, que o frontend segue a arquitetura de autenticação:
//   Supabase Auth = identidade | PostgreSQL (via GET /api/v1/auth/me) = dados do usuário.
// Uso: npm run test:auth
import { readdirSync, readFileSync, existsSync, statSync } from "node:fs";
import { join } from "node:path";

const falhas = [];

function arquivos(dir) {
  return readdirSync(dir).flatMap((nome) => {
    const caminho = join(dir, nome);
    return statSync(caminho).isDirectory() ? arquivos(caminho) : [caminho];
  });
}

const codigo = arquivos("src").filter((f) => /\.(ts|tsx|js|jsx)$/.test(f));

// 1. O frontend não consulta tabela de usuários do Supabase para descobrir o perfil.
for (const f of codigo) {
  const texto = readFileSync(f, "utf8");
  if (/\.from\(\s*["'`]usuarios["'`]\s*\)/i.test(texto)) {
    falhas.push(`${f}: consulta a tabela "Usuarios" do Supabase (o perfil deve vir de /auth/me)`);
  }
}

// 2. O AuthProvider obtém o usuário do backend.
const auth = readFileSync("src/lib/auth.tsx", "utf8");
if (!auth.includes("buscarUsuarioAtual")) falhas.push("src/lib/auth.tsx não usa buscarUsuarioAtual()");
if (/supabase\s*\.\s*from\(/.test(auth)) falhas.push("src/lib/auth.tsx usa supabase.from(...)");
const api = readFileSync("src/lib/api.ts", "utf8");
if (!api.includes('"/auth/me"')) falhas.push('src/lib/api.ts não chama "/auth/me"');
if (!api.includes("Authorization: `Bearer ${token}`")) falhas.push("api.ts não envia o Bearer token");

// 3. Nenhum segredo do backend no frontend.
for (const f of codigo) {
  if (/service_role|SUPABASE_JWT_SECRET|SERVICE_ROLE/i.test(readFileSync(f, "utf8"))) {
    falhas.push(`${f}: referência a segredo do Supabase no código do frontend`);
  }
}
for (const env of [".env", ".env.local", ".env.example"]) {
  if (!existsSync(env)) continue;
  for (const linha of readFileSync(env, "utf8").split(/\r?\n/)) {
    if (/^NEXT_PUBLIC_\w*(SECRET|SERVICE|JWT)\w*\s*=/i.test(linha)) {
      falhas.push(`${env}: variável NEXT_PUBLIC_* com cara de segredo (${linha.split("=")[0]})`);
    }
  }
}

if (falhas.length) {
  console.error("FALHOU:\n - " + falhas.join("\n - "));
  process.exit(1);
}
console.log("OK: perfil vem de /auth/me; nenhuma consulta a Usuarios no Supabase; nenhum segredo no frontend.");