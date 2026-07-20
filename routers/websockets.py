# routers/websockets.py — WebSockets autenticados via cookie (portal web)
#
# Dois endpoints:
#   /ws/notificacoes  — notificações gerais (novo chamado, status, msg)
#   /ws/chat/{id}     — sala de chat em tempo real por chamado

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import json
from crud.users import get_user_by_id
from crud.crud_chamados import buscar_chamado
from .connection_manager import manager
from .desktop_api import _criar_mensagem, _salvar_mensagem, notificar_nova_mensagem

router = APIRouter(tags=["WebSocket Web"])


@router.websocket("/ws/notificacoes")
async def ws_notificacoes_web(websocket: WebSocket):
    """
    WebSocket de notificações para o portal web.
    Autenticação via cookie 'maqcontrol_auth'.
    Recebe: novo_chamado | nova_mensagem | atualizacao_chamado
    """
    session_token = websocket.cookies.get("maqcontrol_auth")
    if not session_token:
        await websocket.close(code=4001)
        return

    user = get_user_by_id(session_token)
    if not user:
        await websocket.close(code=4001)
        return

    await manager.connect(websocket, user_id=user.id, is_admin=user.is_admin)

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"tipo": "pong"})
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id=user.id)


@router.websocket("/ws/chat/{chamado_id}")
async def ws_chat_web(websocket: WebSocket, chamado_id: str):
    """
    WebSocket para chat em tempo real de um chamado específico.
    Autenticação via cookie 'maqcontrol_auth'.
    Recebe: nova_mensagem_chat
    """
    session_token = websocket.cookies.get("maqcontrol_auth")
    if not session_token:
        await websocket.close(code=4001)
        return

    user = get_user_by_id(session_token)
    if not user:
        await websocket.close(code=4001)
        return

    chamado = buscar_chamado(chamado_id)
    if not chamado:
        await websocket.close(code=4004)
        return

    if chamado.usuario_id != user.id and not user.is_admin:
        await websocket.close(code=4003)
        return

    await manager.connect_chat(websocket, chamado_id, user.id, user.is_admin)

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"tipo": "pong"})
                continue

            try:
                payload = json.loads(data)
                msg_texto = payload.get("mensagem", "").strip()
                if msg_texto:
                    message = _criar_mensagem(
                        chamado_id=chamado_id,
                        remetente_id=user.id,
                        remetente_nome=user.name,
                        mensagem=msg_texto,
                        is_admin=user.is_admin
                    )
                    _salvar_mensagem(chamado_id, message)
                    
                    # Envia a mensagem para todos os participantes na sala do chamado
                    await manager.send_to_chat_room(chamado_id, {"tipo": "nova_mensagem_chat", **message})
                    
                    # Dispara as notificações globais para os outros usuários
                    await notificar_nova_mensagem(message, chamado)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await manager.disconnect_chat(websocket, chamado_id)
