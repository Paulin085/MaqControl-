from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime

from crud.crud_chamados import listar_chamados, buscar_chamado
from crud import listar_setores
from models.chamado import StatusChamado
from routers.desktop_api import (
    _load_chat,
    mark_chat_read,
    get_unread_count,
)

router = APIRouter(prefix="/chat", tags=["Chat"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def chat_workspace(request: Request, c: Optional[str] = Query(None)):
    user = request.state.user

    # 1. Carrega todos os chamados disponíveis para o usuário
    todos_chamados = listar_chamados()
    if not user.is_admin:
        usuario_chamados = [ch for ch in todos_chamados if ch.usuario_id == user.id]
    else:
        usuario_chamados = todos_chamados

    # 2. Carrega as mensagens de todos os chamados para pegar a última mensagem e ordenar
    chat_data = _load_chat()

    conversas = []
    for ch in usuario_chamados:
        mensagens_ch = chat_data.get(ch.id, [])
        
        # Última mensagem
        last_msg = ""
        last_msg_time = ch.data_registro
        if mensagens_ch:
            ultima = mensagens_ch[-1]
            last_msg = ultima.get("mensagem", "")
            try:
                last_msg_time = datetime.fromisoformat(ultima.get("timestamp", ""))
            except ValueError:
                pass

        # Contagem de não lidas
        unread_cnt = get_unread_count(user.id, ch.id, user_is_admin=user.is_admin)

        conversas.append({
            "id": ch.id,
            "titulo": ch.titulo or "Chamado sem título",
            "solicitante": ch.solicitante or "",
            "setor": ch.setor_loja or "",
            "status": ch.status.value,
            "dificuldade": ch.dificuldade.value,
            "last_msg": last_msg,
            "last_msg_time": last_msg_time,
            "unread_count": unread_cnt if unread_cnt > 0 else 0
        })

    # Ordenar por data da última mensagem/registro (mais recente primeiro)
    conversas.sort(key=lambda x: x["last_msg_time"], reverse=True)

    # Se colaborador acessou sem ?c=, seleciona automaticamente seu chamado mais recente
    if not c and not user.is_admin and conversas:
        c = conversas[0]["id"]

    # 3. Se selecionou um chamado específico
    chamado_selecionado = None
    mensagens_selecionadas = []
    if c:
        chamado_selecionado = buscar_chamado(c)
        if not chamado_selecionado:
            raise HTTPException(status_code=404, detail="Chamado não encontrado")

        if chamado_selecionado.usuario_id != user.id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Sem permissão para este chat")

        # Marca como lido
        mark_chat_read(user.id, c)
        mensagens_selecionadas = chat_data.get(c, [])

        # Zera contagem de não lida na lista para o chat ativo
        for conv in conversas:
            if conv["id"] == c:
                conv["unread_count"] = 0

    return templates.TemplateResponse(
        request=request,
        name="chat_page.html",
        context={
            "request": request,
            "user": user,
            "conversas": conversas,
            "chamado": chamado_selecionado,
            "mensagens": mensagens_selecionadas,
            "hoje_str": datetime.now().strftime("%Y-%m-%d")
        }
    )
