from typing import List, Optional
from datetime import datetime
from models.chamado import Chamado, ChamadoCreate, ChamadoUpdate, read_all_chamados, write_all_chamados, generate_id

def listar_chamados() -> List[Chamado]:
    """Lista todos os chamados."""
    return read_all_chamados()

def buscar_chamado(chamado_id: str) -> Optional[Chamado]:
    """Busca um chamado pelo ID."""
    chamados = read_all_chamados()
    for c in chamados:
        if c.id == chamado_id:
            return c
    return None

def criar_chamado(payload: ChamadoCreate) -> Chamado:
    """Cria um novo chamado."""
    chamados = read_all_chamados()
    novo_chamado = Chamado(
        id=generate_id(),
        **payload.model_dump()
    )
    chamados.append(novo_chamado)
    write_all_chamados(chamados)
    return novo_chamado

def atualizar_chamado(chamado_id: str, payload: ChamadoUpdate) -> Optional[Chamado]:
    """Atualiza um chamado existente."""
    chamados = read_all_chamados()
    for i, c in enumerate(chamados):
        if c.id == chamado_id:
            update_data = payload.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(c, key, value)
            chamados[i] = c
            write_all_chamados(chamados)
            return c
    return None

def deletar_chamado(chamado_id: str) -> bool:
    """Deleta um chamado."""
    chamados = read_all_chamados()
    for i, c in enumerate(chamados):
        if c.id == chamado_id:
            chamados.pop(i)
            write_all_chamados(chamados)
            return True
    return False
