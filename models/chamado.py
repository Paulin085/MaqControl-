import json
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

# Enums for difficulty and status
class Dificuldade(str, Enum):
    BAIXA = "Baixa"
    MEDIA = "Média"
    ALTA = "Alta"
    CRITICA = "Crítica"

class StatusChamado(str, Enum):
    FILA = "Fila"
    EM_ANDAMENTO = "Em Andamento"
    CONCLUIDO = "Concluído"

class TipoChamado(str, Enum):
    CHAMADO = "Chamado"
    DEMANDA = "Demanda"

# Base model shared fields
class ChamadoBase(BaseModel):
    setor_loja: Optional[str] = Field(None, description="Setor ou loja responsável")
    solicitante: Optional[str] = Field(None, description="Nome do solicitante")
    titulo: Optional[str] = Field(None, description="Título da demanda")
    tipo: TipoChamado = Field(TipoChamado.CHAMADO, description="Tipo do registro")
    dificuldade: Dificuldade = Field(..., description="Nível de dificuldade")
    descricao: str = Field(..., description="Descrição detalhada do chamado")
    resolucao: Optional[str] = Field(None, description="Descrição da solução aplicada")
    status: StatusChamado = Field(StatusChamado.FILA, description="Status atual")
    data_registro: datetime = Field(default_factory=datetime.utcnow, description="Timestamp de criação")
    anexo_path: Optional[str] = Field(None, description="Caminho relativo ao arquivo de anexo")
    usuario_id: Optional[str] = Field(None, description="ID do usuário que registrou o chamado")

# Model for creation (id generated automatically)
class ChamadoCreate(ChamadoBase):
    pass

# Model for updates (all fields optional except id)
class ChamadoUpdate(BaseModel):
    setor_loja: Optional[str] = None
    solicitante: Optional[str] = None
    titulo: Optional[str] = None
    tipo: Optional[TipoChamado] = None
    dificuldade: Optional[Dificuldade] = None
    descricao: Optional[str] = None
    resolucao: Optional[str] = None
    status: Optional[StatusChamado] = None
    anexo_path: Optional[str] = None
    usuario_id: Optional[str] = None

# Full model stored in JSON
class Chamado(ChamadoBase):
    id: str = Field(..., description="UUID do chamado")

    model_config = {"from_attributes": True}

# Helper paths
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHAMADOS_FILE = DATA_DIR / "chamados.json"

def _load_all() -> List[Chamado]:
    if not CHAMADOS_FILE.exists():
        CHAMADOS_FILE.write_text("[]", encoding="utf-8")
        return []
    with CHAMADOS_FILE.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Chamado(**item) for item in raw]

def _save_all(chamados: List[Chamado]):
    with CHAMADOS_FILE.open("w", encoding="utf-8") as f:
        json.dump([c.model_dump() for c in chamados], f, ensure_ascii=False, indent=2, default=str)

def generate_id() -> str:
    return str(uuid.uuid4())

# Exported functions used by CRUD layer
def read_all_chamados() -> List[Chamado]:
    return _load_all()

def write_all_chamados(chamados: List[Chamado]):
    _save_all(chamados)
