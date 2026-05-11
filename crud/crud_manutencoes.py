# crud/crud_manutencoes.py — CRUD de Manutenções
from typing import Optional
from datetime import date

from .config import ARQUIVO_MANUTENCOES
from models.manutencao import Manutencao, ManutencaoCreate
from crud._json_utils import _ler_json, _salvar_json, _gerar_id
from crud.crud_maquinas import atualizar_ultima_manutencao


def listar_manutencoes() -> list[Manutencao]:
    """Retorna todas as manutenções registradas."""
    dados = _ler_json(ARQUIVO_MANUTENCOES)
    return [Manutencao(**m) for m in dados]


def listar_manutencoes_da_maquina(maquina_id: str) -> list[Manutencao]:
    """Retorna o histórico de manutenções de uma máquina específica, ordenado por data."""
    dados = _ler_json(ARQUIVO_MANUTENCOES)
    historico = [Manutencao(**m) for m in dados if m["maquina_id"] == maquina_id]
    return sorted(historico, key=lambda x: x.data_manutencao, reverse=True)


def criar_manutencao(payload: ManutencaoCreate) -> Manutencao:
    """Registra uma nova manutenção e atualiza o status da máquina."""
    dados = _ler_json(ARQUIVO_MANUTENCOES)

    # Converte date para string para serialização
    dados_dict = payload.model_dump()
    if isinstance(dados_dict.get("data_manutencao"), date):
        dados_dict["data_manutencao"] = dados_dict["data_manutencao"].isoformat()

    nova = {"id": _gerar_id(), **dados_dict}
    dados.append(nova)
    _salvar_json(ARQUIVO_MANUTENCOES, dados)

    # Atualiza a última manutenção na máquina (recalcula status e próxima data)
    data = payload.data_manutencao
    if isinstance(data, str):
        data = date.fromisoformat(data)
    atualizar_ultima_manutencao(payload.maquina_id, data)

    return Manutencao(**nova)


def deletar_manutencao(manutencao_id: str) -> bool:
    """Remove um registro de manutenção pelo ID."""
    dados = _ler_json(ARQUIVO_MANUTENCOES)
    novos = [m for m in dados if m["id"] != manutencao_id]
    if len(novos) == len(dados):
        return False
    _salvar_json(ARQUIVO_MANUTENCOES, novos)
    return True
