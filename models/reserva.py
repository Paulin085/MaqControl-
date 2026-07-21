# models/reserva.py — Modelo de Reserva de Salas
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from enum import Enum


class StatusReserva(str, Enum):
    AGENDADA = "Agendada"
    CANCELADA = "Cancelada"
    CONCLUIDA = "Concluída"


class SalaOpcoes(str, Enum):
    REUNIAO = "Sala de Reunião"
    TREINAMENTO = "Sala de Treinamento"


class ReservaCreate(BaseModel):
    sala: SalaOpcoes = Field(..., description="Sala reservada")
    titulo: str = Field(..., min_length=1, max_length=150, description="Título do agendamento")
    descricao: Optional[str] = Field(None, max_length=1000, description="Descrição detalhada")
    data: date = Field(..., description="Data da reserva")
    hora_inicio: str = Field(..., description="Hora de início (HH:MM)")
    hora_fim: str = Field(..., description="Hora de término (HH:MM)")
    participantes: Optional[str] = Field(None, max_length=1000, description="Participantes/convidados")
    observacoes: Optional[str] = Field(None, max_length=1000, description="Observações gerais")


class ReservaUpdate(BaseModel):
    sala: Optional[SalaOpcoes] = None
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    data: Optional[date] = None
    hora_inicio: Optional[str] = None
    hora_fim: Optional[str] = None
    participantes: Optional[str] = None
    observacoes: Optional[str] = None
    status: Optional[StatusReserva] = None


class Reserva(ReservaCreate):
    id: str = Field(..., description="Identificador único (UUID)")
    usuario_id: str = Field(..., description="ID do criador da reserva")
    status: StatusReserva = Field(StatusReserva.AGENDADA, description="Status da reserva")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Data de criação")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Data de última atualização")

    model_config = {"from_attributes": True}
