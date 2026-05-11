# crud/crud_maquinas.py — CRUD completo de Máquinas
from typing import Optional
from datetime import date, timedelta

from .config import ARQUIVO_MAQUINAS, ARQUIVO_SETORES, DIAS_ALERTA_MANUTENCAO
from models.maquina import Maquina, MaquinaCreate, MaquinaUpdate, StatusMaquina
from crud._json_utils import _ler_json, _salvar_json, _gerar_id


def calcular_status(
    ultima_manutencao: Optional[date],
    proxima_manutencao: Optional[date]
) -> StatusMaquina:
    """Calcula o status da máquina com base nas datas de manutenção."""
    hoje = date.today()

    if proxima_manutencao is None:
        return StatusMaquina.SEM_MANUTENCAO

    if hoje > proxima_manutencao:
        return StatusMaquina.PRECISA_MANUTENCAO

    dias_restantes = (proxima_manutencao - hoje).days
    if dias_restantes <= DIAS_ALERTA_MANUTENCAO:
        return StatusMaquina.MANUTENCAO_PROXIMA

    return StatusMaquina.OK


def _calcular_proxima_manutencao(
    ultima_manutencao: Optional[date],
    intervalo_dias: Optional[int]
) -> Optional[date]:
    """Calcula a data da próxima manutenção preventiva."""
    if ultima_manutencao is None or intervalo_dias is None:
        return None
    return ultima_manutencao + timedelta(days=intervalo_dias)


def _intervalo_efetivo(m: dict) -> Optional[int]:
    """Retorna o intervalo de manutenção da máquina ou, como fallback, o do setor."""
    intervalo = m.get("intervalo_manutencao_dias")
    if intervalo:
        return intervalo
    # Fallback: busca o intervalo padrão do setor
    setor_id = m.get("setor_id")
    if setor_id:
        setores = _ler_json(ARQUIVO_SETORES)
        for s in setores:
            if s.get("id") == setor_id:
                return s.get("intervalo_manutencao_dias")
    return None


def _enriquecer_com_status(m: dict) -> dict:
    """Recalcula e injeta status e próxima manutenção no dicionário da máquina."""
    ultima = m.get("ultima_manutencao")
    if ultima and isinstance(ultima, str):
        ultima = date.fromisoformat(ultima)

    intervalo = _intervalo_efetivo(m)
    proxima = _calcular_proxima_manutencao(ultima, intervalo)
    status  = calcular_status(ultima, proxima)

    m["proxima_manutencao"] = proxima.isoformat() if proxima else None
    m["status"] = status.value
    return m


def listar_maquinas(
    setor_id: Optional[str] = None,
    tipo: Optional[str] = None,
    status: Optional[str] = None
) -> list[Maquina]:
    """Retorna máquinas com filtros opcionais por setor, tipo ou status."""
    dados = _ler_json(ARQUIVO_MAQUINAS)
    resultado = []

    for m in dados:
        m = _enriquecer_com_status(m)

        if setor_id and m.get("setor_id") != setor_id:
            continue
        if tipo and m.get("tipo") != tipo:
            continue
        if status and m.get("status") != status:
            continue

        resultado.append(Maquina(**m))

    return resultado


def buscar_maquina(maquina_id: str) -> Optional[Maquina]:
    """Busca uma máquina pelo ID."""
    dados = _ler_json(ARQUIVO_MAQUINAS)
    for m in dados:
        if m["id"] == maquina_id:
            return Maquina(**_enriquecer_com_status(m))
    return None


def criar_maquina(payload: MaquinaCreate) -> Maquina:
    """Cria uma nova máquina no sistema."""
    dados = _ler_json(ARQUIVO_MAQUINAS)

    nova = {
        "id": _gerar_id(),
        "data_cadastro": date.today().isoformat(),
        "ultima_manutencao": None,
        "proxima_manutencao": None,
        "status": StatusMaquina.SEM_MANUTENCAO.value,
        **payload.model_dump(),
    }

    # Converte date para string se necessário
    if nova.get("data_aquisicao") and not isinstance(nova["data_aquisicao"], str):
        nova["data_aquisicao"] = nova["data_aquisicao"].isoformat()

    dados.append(nova)
    _salvar_json(ARQUIVO_MAQUINAS, dados)
    return Maquina(**_enriquecer_com_status(nova))


def atualizar_maquina(maquina_id: str, payload: MaquinaUpdate) -> Optional[Maquina]:
    """Atualiza os campos informados de uma máquina."""
    dados = _ler_json(ARQUIVO_MAQUINAS)
    for i, m in enumerate(dados):
        if m["id"] == maquina_id:
            atualizacoes = payload.model_dump(exclude_none=True)
            # Converte date para string
            for campo in ("data_aquisicao",):
                if campo in atualizacoes and not isinstance(atualizacoes[campo], str):
                    atualizacoes[campo] = atualizacoes[campo].isoformat() if atualizacoes[campo] else None
            dados[i].update(atualizacoes)
            dados[i] = _enriquecer_com_status(dados[i])
            _salvar_json(ARQUIVO_MAQUINAS, dados)
            return Maquina(**dados[i])
    return None


def deletar_maquina(maquina_id: str) -> bool:
    """Remove uma máquina pelo ID."""
    dados = _ler_json(ARQUIVO_MAQUINAS)
    novos = [m for m in dados if m["id"] != maquina_id]
    if len(novos) == len(dados):
        return False
    _salvar_json(ARQUIVO_MAQUINAS, novos)
    return True


def atualizar_ultima_manutencao(maquina_id: str, data_manutencao: date) -> Optional[Maquina]:
    """Atualiza a data da última manutenção e recalcula o status.
    Chamado automaticamente após registrar uma nova manutenção.
    """
    dados = _ler_json(ARQUIVO_MAQUINAS)
    for i, m in enumerate(dados):
        if m["id"] == maquina_id:
            dados[i]["ultima_manutencao"] = data_manutencao.isoformat()
            dados[i] = _enriquecer_com_status(dados[i])
            _salvar_json(ARQUIVO_MAQUINAS, dados)
            return Maquina(**dados[i])
    return None
