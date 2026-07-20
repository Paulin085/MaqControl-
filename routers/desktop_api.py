# routers/desktop_api.py — API para Aplicação Desktop + Chat Web
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from pathlib import Path
import json
import uuid

from crud.crud_chamados import criar_chamado, listar_chamados, buscar_chamado, atualizar_chamado
from models.chamado import ChamadoCreate, ChamadoUpdate, StatusChamado, TipoChamado, Dificuldade, Chamado
from crud.users import get_user_by_email, get_user_by_id, verify_password
from .connection_manager import manager

router = APIRouter(prefix="/api/desktop", tags=["Desktop API"])

# ── Persistência de Chat ──────────────────────────────────────────────────────

_DATA_DIR = Path("data")
_CHAT_FILE = _DATA_DIR / "chat_messages.json"
_READ_FILE = _DATA_DIR / "chat_read.json"
_SESSIONS_FILE = _DATA_DIR / "desktop_sessions.json"


def _load_chat() -> dict:
    """Carrega todas as mensagens de chat do arquivo JSON."""
    if not _CHAT_FILE.exists():
        return {}
    try:
        with _CHAT_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_chat(data: dict) -> None:
    """Salva todas as mensagens de chat no arquivo JSON."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _CHAT_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_read_status() -> dict:
    """Carrega status de leitura: {user_id: {chamado_id: timestamp}}."""
    if not _READ_FILE.exists():
        return {}
    try:
        with _READ_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_read_status(data: dict) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _READ_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def mark_chat_read(user_id: str, chamado_id: str) -> None:
    """Marca todas as mensagens de um chamado como lidas para o usuário."""
    data = _load_read_status()
    data.setdefault(user_id, {})[chamado_id] = datetime.now().isoformat()
    _save_read_status(data)


def get_unread_count(user_id: str, chamado_id: str, user_is_admin: bool) -> int:
    """Retorna o número de mensagens não lidas do outro lado (TI ↔ Colaborador)."""
    read_data = _load_read_status()
    last_read_str = read_data.get(user_id, {}).get(chamado_id)

    chat_data = _load_chat()
    messages = chat_data.get(chamado_id, [])

    def is_from_other_side(msg: dict) -> bool:
        return bool(msg.get("is_admin")) != user_is_admin

    if not last_read_str:
        return sum(1 for m in messages if is_from_other_side(m))

    last_read = datetime.fromisoformat(last_read_str)
    return sum(
        1 for m in messages
        if is_from_other_side(m)
        and datetime.fromisoformat(m["timestamp"]) > last_read
    )


def _load_sessions() -> dict:
    """Carrega sessões desktop do arquivo JSON."""
    if not _SESSIONS_FILE.exists():
        return {}
    try:
        with _SESSIONS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_sessions(data: dict) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _SESSIONS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Modelos ───────────────────────────────────────────────────────────────────

class DesktopAuthRequest(BaseModel):
    email: str
    password: str
    device_name: str


class DesktopAuthResponse(BaseModel):
    status: str
    token: str
    user_id: str
    user_name: str
    is_admin: bool


class ChamadoOpenRequest(BaseModel):
    titulo: str
    descricao: str
    tipo: str = TipoChamado.CHAMADO.value
    dificuldade: str = Dificuldade.MEDIA.value
    setor_loja: Optional[str] = None
    solicitante: Optional[str] = None


class ChatMessageRequest(BaseModel):
    mensagem: str


# ── AUTENTICAÇÃO DESKTOP ──────────────────────────────────────────────────────

@router.post("/auth", response_model=DesktopAuthResponse)
async def desktop_auth(auth_request: DesktopAuthRequest):
    """Autentica o desktop e gera um token de acesso persistente."""
    user = get_user_by_email(auth_request.email)

    if not user or not verify_password(auth_request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")

    token = str(uuid.uuid4())
    sessions = _load_sessions()
    sessions[token] = {
        "user_id": user.id,
        "user_name": user.name,
        "email": user.email,
        "is_admin": user.is_admin,
        "device_name": auth_request.device_name,
        "created_at": datetime.now().isoformat()
    }
    _save_sessions(sessions)

    return DesktopAuthResponse(
        status="ok",
        token=token,
        user_id=user.id,
        user_name=user.name,
        is_admin=user.is_admin
    )


def verify_desktop_token(token: str) -> dict:
    """Valida o token do desktop."""
    sessions = _load_sessions()
    if token not in sessions:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    return sessions[token]


# ── CHAMADOS DESKTOP ──────────────────────────────────────────────────────────

@router.post("/chamados/abrir")
async def desktop_abrir_chamado(
    chamado_request: ChamadoOpenRequest,
    token: str = Query(...)
):
    session = verify_desktop_token(token)

    payload = ChamadoCreate(
        titulo=chamado_request.titulo,
        descricao=chamado_request.descricao,
        tipo=TipoChamado(chamado_request.tipo),
        dificuldade=Dificuldade(chamado_request.dificuldade),
        setor_loja=chamado_request.setor_loja,
        solicitante=chamado_request.solicitante,
        status=StatusChamado.FILA,
        resolucao=None,
        data_registro=datetime.now(),
        anexo_path=None,
        usuario_id=session["user_id"]
    )

    chamado = criar_chamado(payload)
    await notificar_novo_chamado(chamado, session["user_name"])

    return {
        "status": "ok",
        "chamado_id": chamado.id,
        "titulo": chamado.titulo,
        "mensagem": "Chamado criado com sucesso!"
    }


@router.get("/chamados/meus")
async def desktop_listar_meus_chamados(token: str = Query(...)):
    session = verify_desktop_token(token)
    todos_chamados = listar_chamados()
    chamados_usuario = [c for c in todos_chamados if c.usuario_id == session["user_id"]]

    chamados_ativos = [
        {
            "id": c.id,
            "titulo": c.titulo,
            "descricao": c.descricao,
            "status": c.status.value,
            "dificuldade": c.dificuldade.value,
            "data_registro": c.data_registro.isoformat(),
            "ultima_atualizacao": c.data_registro.isoformat()
        }
        for c in chamados_usuario if c.status != StatusChamado.CONCLUIDO
    ]

    return {"status": "ok", "total": len(chamados_ativos), "chamados": chamados_ativos}


@router.get("/chamados/{chamado_id}")
async def desktop_get_chamado(chamado_id: str, token: str = Query(...)):
    session = verify_desktop_token(token)
    chamado = buscar_chamado(chamado_id)

    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if chamado.usuario_id != session["user_id"] and not session["is_admin"]:
        raise HTTPException(status_code=403, detail="Sem permissão para acessar este chamado")

    return {
        "status": "ok",
        "chamado": {
            "id": chamado.id,
            "titulo": chamado.titulo,
            "descricao": chamado.descricao,
            "status": chamado.status.value,
            "tipo": chamado.tipo.value,
            "dificuldade": chamado.dificuldade.value,
            "setor_loja": chamado.setor_loja,
            "solicitante": chamado.solicitante,
            "resolucao": chamado.resolucao,
            "data_registro": chamado.data_registro.isoformat(),
            "anexo_path": chamado.anexo_path,
            "usuario_id": chamado.usuario_id
        }
    }


# ── CHAT DESKTOP (token) ──────────────────────────────────────────────────────

@router.post("/chat/enviar")
async def desktop_enviar_mensagem(
    chamado_id: str = Query(...),
    mensagem: str = Query(...),
    token: str = Query(...)
):
    session = verify_desktop_token(token)
    chamado = buscar_chamado(chamado_id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    message = _criar_mensagem(
        chamado_id=chamado_id,
        remetente_id=session["user_id"],
        remetente_nome=session["user_name"],
        mensagem=mensagem,
        is_admin=session["is_admin"]
    )
    _salvar_mensagem(chamado_id, message)
    await notificar_nova_mensagem(message, chamado)
    await manager.send_to_chat_room(chamado_id, {"tipo": "nova_mensagem_chat", **message})

    return {"status": "ok", "mensagem_id": message["id"], "timestamp": message["timestamp"]}


@router.get("/chat/{chamado_id}")
async def desktop_get_chat(chamado_id: str, token: str = Query(...)):
    session = verify_desktop_token(token)
    chamado = buscar_chamado(chamado_id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if chamado.usuario_id != session["user_id"] and not session["is_admin"]:
        raise HTTPException(status_code=403, detail="Sem permissão para acessar este chat")

    mensagens = _load_chat().get(chamado_id, [])
    return {
        "status": "ok",
        "chamado_id": chamado_id,
        "total_mensagens": len(mensagens),
        "mensagens": mensagens
    }


# ── CHAT WEB (cookie) ─────────────────────────────────────────────────────────

@router.get("/web/chat/{chamado_id}")
async def web_get_chat(chamado_id: str, request: Request):
    """Retorna histórico de chat. Autenticado via cookie (portal web)."""
    user = request.state.user
    chamado = buscar_chamado(chamado_id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if chamado.usuario_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Sem permissão para acessar este chat")

    # Marca como lido
    mark_chat_read(user.id, chamado_id)

    mensagens = _load_chat().get(chamado_id, [])
    return {
        "status": "ok",
        "chamado_id": chamado_id,
        "mensagens": mensagens
    }


@router.post("/web/chat/{chamado_id}")
async def web_enviar_mensagem(chamado_id: str, body: ChatMessageRequest, request: Request):
    """Envia mensagem de chat. Autenticado via cookie (portal web)."""
    user = request.state.user
    chamado = buscar_chamado(chamado_id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if chamado.usuario_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Sem permissão para este chat")

    if not body.mensagem.strip():
        raise HTTPException(status_code=400, detail="Mensagem não pode ser vazia")

    message = _criar_mensagem(
        chamado_id=chamado_id,
        remetente_id=user.id,
        remetente_nome=user.name,
        mensagem=body.mensagem.strip(),
        is_admin=user.is_admin
    )
    _salvar_mensagem(chamado_id, message)

    # Notifica via WebSocket
    await manager.send_to_chat_room(chamado_id, {"tipo": "nova_mensagem_chat", **message})
    await notificar_nova_mensagem(message, chamado)

    return {"status": "ok", "mensagem_id": message["id"], "timestamp": message["timestamp"]}


# ── WebSocket Desktop (token) ──────────────────────────────────────────────────

@router.websocket("/ws/notificacoes/{token}")
async def websocket_notificacoes(websocket: WebSocket, token: str):
    """WebSocket de notificações para a aplicação desktop (token auth)."""
    session = verify_desktop_token(token)
    user_id = session["user_id"]
    is_admin = session["is_admin"]

    await manager.connect(websocket, user_id=user_id, is_admin=is_admin)

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"status": "pong"})
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id=user_id)


# ── Funções Auxiliares ────────────────────────────────────────────────────────

def _criar_mensagem(
    chamado_id: str,
    remetente_id: str,
    remetente_nome: str,
    mensagem: str,
    is_admin: bool
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "chamado_id": chamado_id,
        "remetente_id": remetente_id,
        "remetente_nome": remetente_nome,
        "is_admin": is_admin,
        "mensagem": mensagem,
        "timestamp": datetime.now().isoformat(),
        "lido": False
    }


def _salvar_mensagem(chamado_id: str, message: dict) -> None:
    chat_data = _load_chat()
    chat_data.setdefault(chamado_id, []).append(message)
    _save_chat(chat_data)


async def notificar_novo_chamado(chamado, usuario_nome: str):
    """Notifica a equipe de TI sobre um novo chamado."""
    notificacao = {
        "tipo": "novo_chamado",
        "chamado_id": chamado.id,
        "titulo": chamado.titulo,
        "solicitante": usuario_nome,
        "setor": chamado.setor_loja or "",
        "dificuldade": chamado.dificuldade.value,
        "timestamp": datetime.now().isoformat()
    }
    await manager.send_to_admins(notificacao)


async def notificar_nova_mensagem(message: dict, chamado):
    """Notifica os participantes sobre nova mensagem de chat (via canal de notificações)."""
    notificacao = {
        "tipo": "nova_mensagem",
        "chamado_id": message["chamado_id"],
        "chamado_titulo": chamado.titulo or "",
        "remetente": message["remetente_nome"],
        "is_admin": message["is_admin"],
        "preview": message["mensagem"][:80],
        "timestamp": message["timestamp"]
    }
    remetente_id = message["remetente_id"]

    # Colaborador (solicitante) recebe se TI enviou
    if chamado.usuario_id and chamado.usuario_id != remetente_id:
        await manager.send_to_user(chamado.usuario_id, notificacao)

    # TI recebe se colaborador enviou
    await manager.send_to_admins(notificacao, exclude_user_id=remetente_id)


async def notificar_atualizacao_chamado(chamado):
    """Notifica o colaborador + TI sobre mudança de status."""
    notificacao = {
        "tipo": "atualizacao_chamado",
        "chamado_id": chamado.id,
        "chamado_titulo": chamado.titulo or "",
        "novo_status": chamado.status.value,
        "timestamp": datetime.now().isoformat()
    }

    if chamado.usuario_id:
        await manager.send_to_user(chamado.usuario_id, notificacao)

    await manager.send_to_admins(notificacao, exclude_user_id=chamado.usuario_id)
