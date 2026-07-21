# crud/crud_reservas.py — CRUD completo de Reservas de Salas
import os
from typing import Optional, List, Tuple
from datetime import date, datetime, time
from pathlib import Path

from .config import ARQUIVO_RESERVAS
from models.reserva import Reserva, ReservaCreate, ReservaUpdate, StatusReserva, SalaOpcoes
from crud._json_utils import _ler_json, _salvar_json, _gerar_id


# Índices em memória simulados para sala+data e usuário
_index_sala_data = {}  # (sala, date_str) -> list of dict
_index_usuario = {}    # usuario_id -> list of dict


def _carregar_e_indexar() -> List[dict]:
    """Carrega as reservas do JSON e reconstrói os índices em memória."""
    global _index_sala_data, _index_usuario
    dados = _ler_json(ARQUIVO_RESERVAS)

    _index_sala_data.clear()
    _index_usuario.clear()

    for r in dados:
        # Indexa por sala + data
        chave_sala_data = (r.get("sala"), r.get("data"))
        _index_sala_data.setdefault(chave_sala_data, []).append(r)

        # Indexa por usuário
        chave_usr = r.get("usuario_id")
        _index_usuario.setdefault(chave_usr, []).append(r)

    return dados


def time_to_minutes(t_str: str) -> int:
    """Converte string 'HH:MM' em minutos do dia."""
    parts = t_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def verificar_conflito(sala: str, data_reserva: date, hora_inicio: str, hora_fim: str, ignorar_id: Optional[str] = None) -> bool:
    """Retorna True se houver conflito de horário para a sala na data informada."""
    _carregar_e_indexar()
    
    chave = (sala, data_reserva.isoformat() if isinstance(data_reserva, date) else data_reserva)
    reservas_dia = _index_sala_data.get(chave, [])

    start = time_to_minutes(hora_inicio)
    end = time_to_minutes(hora_fim)

    for r in reservas_dia:
        if r.get("id") == ignorar_id:
            continue
        if r.get("status") == StatusReserva.CANCELADA.value:
            continue

        r_start = time_to_minutes(r.get("hora_inicio"))
        r_end = time_to_minutes(r.get("hora_fim"))

        # Conflito se start1 < end2 E start2 < end1
        if start < r_end and r_start < end:
            return True

    return False


def validar_reserva(reserva: ReservaCreate, ignorar_id: Optional[str] = None) -> Tuple[bool, str]:
    """Valida as regras de negócio de uma reserva."""
    # 1. Validar início < fim
    start_min = time_to_minutes(reserva.hora_inicio)
    end_min = time_to_minutes(reserva.hora_fim)
    if start_min >= end_min:
        return False, "A hora de início deve ser menor que a hora de término."

    # 2. Bloquear datas/horários passados
    hoje = date.today()
    if reserva.data < hoje:
        return False, "Não é possível reservar salas em datas passadas."
    
    if reserva.data == hoje:
        agora = datetime.now()
        agora_min = agora.hour * 60 + agora.minute
        if start_min < agora_min:
            return False, "Não é possível reservar salas em horários passados."

    # 3. Não permitir conflito de horários
    if verificar_conflito(reserva.sala.value, reserva.data, reserva.hora_inicio, reserva.hora_fim, ignorar_id):
        return False, f"A {reserva.sala.value} já está reservada no período de {reserva.hora_inicio} às {reserva.hora_fim}."

    return True, ""


def listar_reservas(
    sala: Optional[str] = None,
    data_filtro: Optional[date] = None,
    status: Optional[str] = None,
    usuario_id: Optional[str] = None,
    pesquisa: Optional[str] = None
) -> List[Reserva]:
    """Retorna a lista de reservas aplicando filtros e ordenando por data e hora."""
    dados = _carregar_e_indexar()
    resultado = []

    for r in dados:
        if sala and r.get("sala") != sala:
            continue
        if data_filtro:
            d_filtro_str = data_filtro.isoformat() if isinstance(data_filtro, date) else data_filtro
            if r.get("data") != d_filtro_str:
                continue
        if status and r.get("status") != status:
            continue
        if usuario_id and r.get("usuario_id") != usuario_id:
            continue
        if pesquisa:
            term = pesquisa.lower()
            if term not in r.get("titulo", "").lower() and term not in r.get("descricao", "").lower():
                continue

        resultado.append(Reserva(**r))

    # Ordenação por data e horário de início
    resultado.sort(key=lambda x: (x.data, x.hora_inicio))
    return resultado


def buscar_reserva(reserva_id: str) -> Optional[Reserva]:
    """Busca uma reserva pelo ID."""
    dados = _carregar_e_indexar()
    for r in dados:
        if r.get("id") == reserva_id:
            return Reserva(**r)
    return None


def criar_reserva(payload: ReservaCreate, usuario_id: str) -> Reserva:
    """Cria uma nova reserva no banco (JSON)."""
    dados = _ler_json(ARQUIVO_RESERVAS)

    nova_reserva = Reserva(
        id=_gerar_id(),
        sala=payload.sala,
        titulo=payload.titulo,
        descricao=payload.descricao,
        data=payload.data,
        hora_inicio=payload.hora_inicio,
        hora_fim=payload.hora_fim,
        participantes=payload.participantes,
        observacoes=payload.observacoes,
        usuario_id=usuario_id,
        status=StatusReserva.AGENDADA,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    dados.append(nova_reserva.model_dump())
    _salvar_json(ARQUIVO_RESERVAS, dados)
    return nova_reserva


def atualizar_reserva(reserva_id: str, payload: ReservaUpdate) -> Optional[Reserva]:
    """Atualiza os dados de uma reserva existente."""
    dados = _ler_json(ARQUIVO_RESERVAS)
    for r in dados:
        if r.get("id") == reserva_id:
            # Prepara atualização
            update_dict = payload.model_dump(exclude_unset=True)
            for k, v in update_dict.items():
                if isinstance(v, (date, datetime, StatusReserva, SalaOpcoes)):
                    r[k] = v.value if hasattr(v, "value") else v.isoformat()
                else:
                    r[k] = v
            r["updated_at"] = datetime.utcnow().isoformat()
            
            _salvar_json(ARQUIVO_RESERVAS, dados)
            return Reserva(**r)
    return None


def excluir_reserva(reserva_id: str) -> bool:
    """Exclui permanentemente uma reserva."""
    dados = _ler_json(ARQUIVO_RESERVAS)
    novo_dados = [r for r in dados if r.get("id") != reserva_id]
    if len(novo_dados) < len(dados):
        _salvar_json(ARQUIVO_RESERVAS, novo_dados)
        return True
    return False
