# crud/__init__.py
from .crud_setores import (
    listar_setores, buscar_setor, criar_setor,
    atualizar_setor, deletar_setor
)
from .crud_maquinas import (
    listar_maquinas, buscar_maquina, criar_maquina,
    atualizar_maquina, deletar_maquina, calcular_status
)
from .crud_manutencoes import (
    listar_manutencoes, listar_manutencoes_da_maquina,
    criar_manutencao, deletar_manutencao
)
