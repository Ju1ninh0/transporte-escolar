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
  nome: string;
  email: string;
  telefone: string | null;
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

export type StatusMensalidade =
  | "PENDENTE"
  | "PAGO"
  | "ATRASADO"
  | "CANCELADO";

export type MetodoPagamento =
  | "PIX"
  | "DINHEIRO"
  | "TRANSFERENCIA"
  | "OUTRO";

export interface Pagamento {
  id: number;
  mensalidade_id: number;
  valor: string;
  data_pagamento: string | null;
  metodo: string;
  comprovante: string | null;
  created_at: string;
}

export interface Mensalidade {
  id: number;
  aluno_id: number;
  aluno_nome: string;
  responsavel_id: number;
  responsavel_nome: string;
  mes_referencia: string;
  valor: string;
  valor_pago: string;
  saldo: string;
  vencimento: string;
  status: StatusMensalidade;
  created_at: string;
  updated_at: string;
}

export interface MensalidadeDetalhe extends Mensalidade {
  pagamentos: Pagamento[];
}

export interface ResumoFinanceiro {
  total_previsto: string;
  total_recebido: string;
  total_pendente: string;
  total_atrasado: string;
}

export type Responsavel = {
  nome: string;
  email: string;
  telefone: string | null;
  id: number;
  usuario_id: number;
  endereco: string | null;
};

export type Gravidade = "LEVE" | "MEDIA" | "GRAVE";

export const GRAVIDADES: { value: Gravidade; label: string }[] = [
  { value: "LEVE", label: "Leve" },
  { value: "MEDIA", label: "Média" },
  { value: "GRAVE", label: "Grave" },
];

export type TipoOcorrencia = { id: number; nome: string; ativo: boolean };

export type Ocorrencia = {
  id: number;
  aluno_id: number;
  aluno_nome: string;
  tipo_id: number;
  tipo_nome: string;
  data: string;
  gravidade: Gravidade;
  descricao: string;
  consequencia: string | null;
  registrado_por: number;
  registrado_por_nome: string;
  created_at: string;
};

export type SugestaoConsequencia = {
  aluno_id: number;
  numero_ocorrencia: number;
  consequencia: string | null;
};

export type PixConfig = {
  recebedor: string;
  tipo_chave: string;
  chave: string;
  mensagem: string;
};

export type RegraReincidencia = { numero_ocorrencia: number; consequencia: string };

export type Configuracoes = {
  pix: Partial<PixConfig> | null;
  proximidade_metros: number | null;
  regras_reincidencia: RegraReincidencia[];
};