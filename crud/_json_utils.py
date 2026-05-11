# crud/_json_utils.py — Helpers internos para leitura/escrita de JSON
import json
import uuid
from pathlib import Path
from typing import Any


def _ler_json(caminho: Path) -> list[dict]:
    """Lê um arquivo JSON e retorna uma lista de dicionários.
    Se o arquivo não existir ou estiver vazio, retorna lista vazia.
    """
    if not caminho.exists() or caminho.stat().st_size == 0:
        return []
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def _salvar_json(caminho: Path, dados: list[dict]) -> None:
    """Salva uma lista de dicionários em um arquivo JSON formatado."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2, default=str)


def _gerar_id() -> str:
    """Gera um UUID único como string."""
    return str(uuid.uuid4())
