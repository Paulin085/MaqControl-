# models/setor.py — Modelo do Setor
from pydantic import BaseModel, Field
from typing import Optional


class SetorCreate(BaseModel):
    """Dados para criar um novo setor."""
    nome: str = Field(..., min_length=1, max_length=100, description="Nome do setor")
    descricao: Optional[str] = Field(None, max_length=500, description="Descrição opcional")
    intervalo_manutencao_dias: int = Field(
        90, ge=1, le=3650,
        description="Intervalo padrão de manutenção preventiva em dias para este setor"
    )


class SetorUpdate(BaseModel):
    """Dados para atualizar um setor existente."""
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=500)
    intervalo_manutencao_dias: Optional[int] = Field(None, ge=1, le=3650)


class Setor(SetorCreate):
    """Setor completo com ID gerado."""
    id: str = Field(..., description="Identificador único do setor (UUID)")

    model_config = {"from_attributes": True}
