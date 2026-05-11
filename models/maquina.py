# models/maquina.py — Modelo da Máquina
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import date


class TipoMaquina(str, Enum):
    """Tipo de máquina cadastrada."""
    PC_DESKTOP = "PC Desktop"
    NOTEBOOK   = "Notebook"


class StatusMaquina(str, Enum):
    """Status calculado automaticamente com base na manutenção."""
    OK                   = "OK"
    MANUTENCAO_PROXIMA   = "Manutenção Próxima"
    PRECISA_MANUTENCAO   = "Precisa de Manutenção"
    SEM_MANUTENCAO       = "Sem Registro de Manutenção"


class MaquinaCreate(BaseModel):
    """Dados para criar uma nova máquina."""

    # Identificação
    nome: str = Field(..., min_length=1, max_length=100, description="Nome ou hostname da máquina")
    tipo: TipoMaquina = Field(..., description="Tipo: PC Desktop ou Notebook")
    setor_id: str = Field(..., description="ID do setor ao qual a máquina pertence")

    # Rede
    ip: Optional[str] = Field(None, max_length=50, description="Endereço IP da máquina")
    anydesk: Optional[str] = Field(None, max_length=50, description="Número do AnyDesk")

    # Hardware
    processador: Optional[str] = Field(None, max_length=200, description="Modelo do processador")
    memoria_ram: Optional[str] = Field(None, max_length=50, description="Ex: 8GB DDR4")
    armazenamento_tipo: Optional[str] = Field(None, max_length=10, description="HD ou SSD")
    armazenamento_capacidade: Optional[str] = Field(None, max_length=50, description="Ex: 500GB, 1TB")

    # Administrativo
    data_aquisicao: Optional[date] = Field(None, description="Data de aquisição da máquina")
    observacoes: Optional[str] = Field(None, max_length=1000, description="Observações livres")

    # Manutenção
    intervalo_manutencao_dias: Optional[int] = Field(
        None, ge=1, le=3650,
        description="Intervalo personalizado de manutenção (substitui o padrão do setor)"
    )


class MaquinaUpdate(BaseModel):
    """Dados para atualizar uma máquina existente (todos os campos opcionais)."""
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    tipo: Optional[TipoMaquina] = None
    setor_id: Optional[str] = None
    ip: Optional[str] = Field(None, max_length=50)
    anydesk: Optional[str] = Field(None, max_length=50)
    processador: Optional[str] = Field(None, max_length=200)
    memoria_ram: Optional[str] = Field(None, max_length=50)
    armazenamento_tipo: Optional[str] = Field(None, max_length=10)
    armazenamento_capacidade: Optional[str] = Field(None, max_length=50)
    data_aquisicao: Optional[date] = None
    observacoes: Optional[str] = Field(None, max_length=1000)
    intervalo_manutencao_dias: Optional[int] = Field(None, ge=1, le=3650)


class Maquina(MaquinaCreate):
    """Máquina completa com ID, status calculado e timestamps."""
    id: str = Field(..., description="Identificador único da máquina (UUID)")
    status: StatusMaquina = Field(StatusMaquina.SEM_MANUTENCAO, description="Status atual")
    proxima_manutencao: Optional[date] = Field(None, description="Data calculada da próxima manutenção")
    ultima_manutencao: Optional[date] = Field(None, description="Data da última manutenção registrada")
    data_cadastro: date = Field(..., description="Data em que a máquina foi cadastrada no sistema")

    model_config = {"from_attributes": True}
