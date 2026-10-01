export type Perfil = "ADMIN" | "MOTORISTA" | "RESPONSAVEL";

export type Usuario = {
  id: number;
  nome: string;
  email: string;
  telefone: string | null;
  perfil: Perfil;
};

export type Motorista = {
  id: number;
  usuario_id: number;
};

export type Aluno = {
  id: number;
  nome: string;
  data_nascimento: string;
  escola: string;
  serie: string | null;
  responsavel_id: number;
  ativo: boolean;
};

export const homePorPerfil: Record<Perfil, string> = {
  ADMIN: "/admin",
  MOTORISTA: "/motorista",
  RESPONSAVEL: "/responsavel",
};

export const fmtData = (iso: string) => iso.split("-").reverse().join("/");