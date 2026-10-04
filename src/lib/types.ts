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

export type Veiculo = {
  id: number;
  placa: string;
  apelido: string;
  capacidade: number;
  ativo: boolean;
};

export type StatusRota = "ATIVA" | "INATIVA";

export type RotaResumo = {
  id: number;
  nome: string;
  escola: string | null;
  status: StatusRota;
  veiculo: { id: number; placa: string; apelido: string } | null;
  motorista: { id: number; nome: string } | null;
  total_paradas: number;
  total_alunos: number;
};

export type Parada = {
  id: number;
  rota_id: number;
  nome: string;
  latitude: number;
  longitude: number;
  ordem: number;
};

export type RotaAluno = {
  aluno_id: number;
  nome: string;
  escola: string;
  parada_id: number | null;
  parada_nome: string | null;
};

export type RotaDetalhe = RotaResumo & { paradas: Parada[]; alunos: RotaAluno[] };

export type StatusViagem = "EM_ANDAMENTO" | "FINALIZADA";

export type Viagem = {
  id: number;
  rota_id: number;
  rota_nome: string;
  veiculo_id: number | null;
  motorista_id: number | null;
  motorista_nome: string | null;
  iniciada_em: string;
  finalizada_em: string | null;
  status: StatusViagem;
};

export type MotoristaRota = RotaResumo & { viagem_em_andamento_id: number | null };

export type MotoristaRotaDetalhe = MotoristaRota & { paradas: Parada[]; alunos: RotaAluno[] };

export type StatusPresenca = "PRESENTE" | "FALTA";

export type PresencaAluno = {
  aluno_id: number;
  nome: string;
  escola: string;
  parada_id: number | null;
  parada_nome: string | null;
  status: StatusPresenca | null;
  observacao: string | null;
  registrado_em: string | null;
};

export type Presencas = {
  viagem_id: number;
  status_viagem: StatusViagem;
  total: number;
  presentes: number;
  faltas: number;
  pendentes: number;
  alunos: PresencaAluno[];
};

export type PosicaoVan = {
  latitude: number;
  longitude: number;
  velocidade: number | null;
  direcao: number | null;
  timestamp: string;
};

export type ViagemAtiva = {
  viagem_id: number;
  rota_id: number;
  rota_nome: string;
  veiculo_apelido: string | null;
  veiculo_placa: string | null;
  motorista_nome: string | null;
  iniciada_em: string;
  posicao: PosicaoVan | null;
};

export type PontoTrilha = { latitude: number; longitude: number; timestamp: string };

export type FilhoRota = {
  rota_id: number;
  rota_nome: string;
  parada_id: number | null;
  parada_nome: string | null;
  viagem_em_andamento_id: number | null;
};

export type Filho = {
  id: number;
  nome: string;
  escola: string;
  serie: string | null;
  rotas: FilhoRota[];
};

export type ViagemDoFilho = {
  viagem_id: number;
  iniciada_em: string;
  motorista_nome: string | null;
  posicao: PosicaoVan | null;
  status_chamada: StatusPresenca | null;
};

export type RotaAcompanhamento = {
  rota_id: number;
  rota_nome: string;
  escola: string | null;
  veiculo_apelido: string | null;
  veiculo_placa: string | null;
  motorista_nome: string | null;
  parada_id: number | null;
  parada_nome: string | null;
  paradas: Parada[];
  viagem: ViagemDoFilho | null;
};

export type Acompanhamento = { aluno_id: number; aluno_nome: string; rotas: RotaAcompanhamento[] };

export type PresencaRegistro = {
  viagem_id: number;
  iniciada_em: string;
  rota_nome: string;
  status: StatusPresenca;
  observacao: string | null;
};

export type PresencaHistorico = {
  aluno_id: number;
  aluno_nome: string;
  dias: number;
  presentes: number;
  faltas: number;
  registros: PresencaRegistro[];
};

export type PixInfo = { recebedor: string; tipo_chave: string; chave: string; mensagem: string | null };

export type OcorrenciaFilho = {
  id: number;
  aluno_id: number;
  aluno_nome: string;
  tipo_nome: string;
  data: string;
  gravidade: Gravidade;
  descricao: string;
  consequencia: string | null;
};

export type Aviso = {
  id: number;
  tipo: string;
  titulo: string;
  mensagem: string;
  lida: boolean;
  created_at: string;
};