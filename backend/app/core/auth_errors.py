class ErroAutenticacao(Exception):
    """Falha de autenticação/identidade com código estável, para o cliente distinguir a causa.

    401 = token ausente, inválido ou expirado (não autenticado)
    403 = autenticado, mas sem cadastro ativo no sistema
    503 = não foi possível validar o token (configuração ou JWKS indisponível)
    """

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message