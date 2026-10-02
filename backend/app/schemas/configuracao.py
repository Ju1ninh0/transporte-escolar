from pydantic import BaseModel, ConfigDict, Field


class PixConfig(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    recebedor: str = Field(min_length=1, max_length=120)
    tipo_chave: str = Field(min_length=1, max_length=20)
    chave: str = Field(min_length=1, max_length=140)
    mensagem: str = Field(default="", max_length=140)


class RegraOut(BaseModel):
    numero_ocorrencia: int
    consequencia: str


class ConfiguracoesOut(BaseModel):
    pix: dict | None
    proximidade_metros: int | None
    regras_reincidencia: list[RegraOut]


class ConfiguracoesUpdate(BaseModel):
    pix: PixConfig | None = None
    proximidade_metros: int | None = Field(default=None, gt=0, le=100000)


class RegraUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    consequencia: str = Field(min_length=1, max_length=120)