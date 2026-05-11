# crud/crud_setores.py — CRUD completo de Setores
from typing import Optional
from .config import ARQUIVO_SETORES
from models.setor import Setor, SetorCreate, SetorUpdate
from crud._json_utils import _ler_json, _salvar_json, _gerar_id


def listar_setores() -> list[Setor]:
    """Retorna todos os setores cadastrados."""
    dados = _ler_json(ARQUIVO_SETORES)
    return [Setor(**s) for s in dados]


def buscar_setor(setor_id: str) -> Optional[Setor]:
    """Busca um setor pelo ID. Retorna None se não encontrado."""
    dados = _ler_json(ARQUIVO_SETORES)
    for s in dados:
        if s["id"] == setor_id:
            return Setor(**s)
    return None


def criar_setor(payload: SetorCreate) -> Setor:
    """Cria um novo setor e salva no JSON."""
    dados = _ler_json(ARQUIVO_SETORES)

    # Verifica duplicidade de nome
    nomes_existentes = [s["nome"].lower() for s in dados]
    if payload.nome.lower() in nomes_existentes:
        raise ValueError(f"Já existe um setor com o nome '{payload.nome}'.")

    novo = Setor(id=_gerar_id(), **payload.model_dump())
    dados.append(novo.model_dump())
    _salvar_json(ARQUIVO_SETORES, dados)
    return novo


def atualizar_setor(setor_id: str, payload: SetorUpdate) -> Optional[Setor]:
    """Atualiza os campos informados de um setor. Retorna None se não encontrado."""
    dados = _ler_json(ARQUIVO_SETORES)
    for i, s in enumerate(dados):
        if s["id"] == setor_id:
            atualizacoes = payload.model_dump(exclude_none=True)
            dados[i].update(atualizacoes)
            _salvar_json(ARQUIVO_SETORES, dados)
            return Setor(**dados[i])
    return None


def deletar_setor(setor_id: str) -> bool:
    """Remove um setor pelo ID. Retorna True se deletado, False se não encontrado."""
    dados = _ler_json(ARQUIVO_SETORES)
    novos = [s for s in dados if s["id"] != setor_id]
    if len(novos) == len(dados):
        return False  # Não encontrado
    _salvar_json(ARQUIVO_SETORES, novos)
    return True
