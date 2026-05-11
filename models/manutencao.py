# models/manutencao.py — Modelo de Manutenção
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class ManutencaoCreate(BaseModel):
    """Dados para registrar uma nova manutenção."""
    maquina_id: str = Field(..., description="ID da máquina que recebeu manutenção")
    data_manutencao: date = Field(..., description="Data em que a manutenção foi realizada")
    descricao: str = Field(..., min_length=1, max_length=2000, description="O que foi feito")
    responsavel: str = Field(..., min_length=1, max_length=100, description="Nome do responsável")
    tipo: str = Field("Preventiva", description="Tipo: Preventiva ou Corretiva")
    observacoes: Optional[str] = Field(None, max_length=1000)


class Manutencao(ManutencaoCreate):
    """Manutenção completa com ID gerado."""
    id: str = Field(..., description="Identificador único do registro (UUID)")

    model_config = {"from_attributes": True}
