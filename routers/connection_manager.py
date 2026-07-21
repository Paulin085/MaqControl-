# routers/connection_manager.py — Gerenciador central de conexões WebSocket
#
# Gerencia dois tipos de conexão:
#   1. Notificações gerais (user_id) — novo chamado, status, mensagem
#   2. Salas de Chat por chamado (chamado_id) — mensagens em tempo real
#
# Permite:
#   - enviar para um usuário específico
#   - enviar para toda a equipe de TI (admins)
#   - enviar para todos numa sala de chat de um chamado
#   - suportar múltiplas abas do mesmo usuário
#   - remover conexões encerradas automaticamente

import asyncio
import logging
from typing import Dict, List, Set, Tuple

from fastapi import WebSocket

logger = logging.getLogger("maqcontrol.ws")


class ConnectionManager:
    def __init__(self) -> None:
        # ── Notificações gerais ───────────────────────────────────────────────
        # user_id -> lista de conexões ativas (multi-aba / multi-dispositivo)
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # user_id dos admins atualmente conectados
        self.admin_users: Set[str] = set()

        # ── Chat por chamado ──────────────────────────────────────────────────
        # chamado_id -> lista de (WebSocket, user_id, is_admin)
        self.chat_connections: Dict[str, List[Tuple[WebSocket, str, bool]]] = {}

        # Protege estruturas contra corrida entre conexões concorrentes
        self._lock = asyncio.Lock()

    # ── Notificações gerais ───────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, user_id: str, is_admin: bool) -> None:
        async with self._lock:
            self.active_connections.setdefault(user_id, []).append(websocket)
            if is_admin:
                self.admin_users.add(user_id)

    async def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        async with self._lock:
            conns = self.active_connections.get(user_id)
            if not conns:
                return
            if websocket in conns:
                conns.remove(websocket)
            if not conns:
                self.active_connections.pop(user_id, None)
                self.admin_users.discard(user_id)

    async def send_to_user(self, user_id: str, message: dict) -> None:
        """Manda para todas as conexões abertas de UM usuário específico."""
        conns = list(self.active_connections.get(user_id, []))
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                logger.warning("Falha ao enviar para user_id=%s, removendo conexão", user_id)
                await self.disconnect(ws, user_id)

    async def send_to_admins(self, message: dict, exclude_user_id: str | None = None) -> None:
        """Manda para todos os admins (equipe de TI) conectados."""
        admin_ids = list(self.admin_users)
        for admin_id in admin_ids:
            if admin_id == exclude_user_id:
                continue
            await self.send_to_user(admin_id, message)

    async def send_to_users(self, user_ids: List[str], message: dict) -> None:
        """Manda para um conjunto específico de usuários."""
        for user_id in set(user_ids):
            await self.send_to_user(user_id, message)

    # ── Chat por chamado ──────────────────────────────────────────────────────

    async def connect_chat(
        self, websocket: WebSocket, chamado_id: str, user_id: str, is_admin: bool
    ) -> None:
        """Conecta um usuário à sala de chat de um chamado específico."""
        async with self._lock:
            if chamado_id not in self.chat_connections:
                self.chat_connections[chamado_id] = []
            self.chat_connections[chamado_id].append((websocket, user_id, is_admin))
            logger.debug("Chat connect: chamado=%s user=%s", chamado_id, user_id)

    async def disconnect_chat(self, websocket: WebSocket, chamado_id: str) -> None:
        """Remove uma conexão da sala de chat."""
        async with self._lock:
            if chamado_id in self.chat_connections:
                self.chat_connections[chamado_id] = [
                    (ws, uid, adm)
                    for ws, uid, adm in self.chat_connections[chamado_id]
                    if ws != websocket
                ]
                if not self.chat_connections[chamado_id]:
                    self.chat_connections.pop(chamado_id, None)

    async def send_to_chat_room(self, chamado_id: str, message: dict) -> None:
        """Envia mensagem para todos conectados à sala de chat de um chamado."""
        conns = list(self.chat_connections.get(chamado_id, []))
        dead: List[WebSocket] = []
        for ws, uid, adm in conns:
            try:
                await ws.send_json(message)
            except Exception:
                logger.warning("Falha ao enviar chat: chamado=%s user=%s", chamado_id, uid)
                dead.append(ws)
        for ws in dead:
            await self.disconnect_chat(ws, chamado_id)


# Instância única compartilhada pela aplicação inteira
manager = ConnectionManager()
