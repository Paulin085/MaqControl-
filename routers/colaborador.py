# routers/colaborador.py — Portal do Colaborador (interface simplificada)
#
# Apenas colaboradores (não-admin) chegam aqui.
# Rotas:
#   GET  /colaborador/              — lista dos próprios chamados (cards de status)
#   GET  /colaborador/novo          — formulário de novo chamado
#   POST /colaborador/novo          — cria chamado e notifica TI
#   GET  /colaborador/chat/{id}     — tela de chat de um chamado

from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime
import os
import shutil

from crud.crud_chamados import criar_chamado, buscar_chamado, listar_chamados
from crud import listar_setores
from models.chamado import ChamadoCreate, Dificuldade, StatusChamado, TipoChamado
from routers.desktop_api import (
    notificar_novo_chamado,
    get_unread_count,
    mark_chat_read,
    _load_chat,
)

router = APIRouter(prefix="/colaborador", tags=["Colaborador"])
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "static/uploads/chamados"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _guard_colaborador(request: Request):
    """Redireciona admins para o portal da TI."""
    user = request.state.user
    if user.is_admin:
        raise HTTPException(status_code=302, headers={"Location": "/"})
    return user


# ── PORTAL (lista de chamados) ─────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse, name="colaborador_portal")
async def portal_colaborador(request: Request):
    user = request.state.user
    if user.is_admin:
        return RedirectResponse(url="/", status_code=303)

    todos = listar_chamados()
    meus_chamados = [c for c in todos if c.usuario_id == user.id]
    meus_chamados.sort(key=lambda c: c.data_registro, reverse=True)

    # Contagens por status para os 3 cards
    em_fila      = [c for c in meus_chamados if c.status == StatusChamado.FILA]
    em_andamento = [c for c in meus_chamados if c.status == StatusChamado.EM_ANDAMENTO]
    concluidos   = [c for c in meus_chamados if c.status == StatusChamado.CONCLUIDO]

    contagens = {
        "fila":      len(em_fila),
        "andamento": len(em_andamento),
        "concluidos": len(concluidos),
    }

    # Conta mensagens não lidas por chamado
    unread = {
        c.id: get_unread_count(user.id, c.id, user_is_admin=False)
        for c in meus_chamados
    }

    return templates.TemplateResponse(
        request=request,
        name="colaborador/portal.html",
        context={
            "request": request,
            "user": user,
            "chamados": meus_chamados,
            "em_fila": em_fila,
            "em_andamento": em_andamento,
            "concluidos": concluidos,
            "contagens": contagens,
            "unread": unread,
        }
    )


# ── NOVO CHAMADO ───────────────────────────────────────────────────────────────

@router.get("/novo", response_class=HTMLResponse, name="colaborador_novo_get")
async def colaborador_novo_get(request: Request):
    user = request.state.user
    if user.is_admin:
        return RedirectResponse(url="/chamados/novo", status_code=303)

    setores = listar_setores()
    return templates.TemplateResponse(
        request=request,
        name="colaborador/novo_chamado.html",
        context={
            "request": request,
            "user": user,
            "setores": setores,
            # dificuldade_options removido: colaborador não escolhe prioridade
        }
    )


@router.post("/novo", name="colaborador_novo_post")
async def colaborador_novo_post(
    request: Request,
    setor_loja: Optional[str] = Form(None),
    assunto: Optional[str] = Form(None),
    descricao: str = Form(...),
    anexo: Optional[UploadFile] = File(None)
):
    user = request.state.user
    if user.is_admin:
        return RedirectResponse(url="/chamados/novo", status_code=303)

    try:
        # Salva anexo se enviado
        anexo_path = None
        if anexo and anexo.filename:
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{anexo.filename}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(anexo.file, buffer)
            anexo_path = f"/static/uploads/chamados/{filename}"

        payload = ChamadoCreate(
            titulo=assunto or "Chamado sem título",
            descricao=descricao,
            tipo=TipoChamado.CHAMADO,
            dificuldade=Dificuldade.MEDIA,   # Sempre Média para colaboradores
            setor_loja=setor_loja,
            solicitante=user.name,
            status=StatusChamado.FILA,
            resolucao=None,
            data_registro=datetime.now(),
            anexo_path=anexo_path,
            usuario_id=user.id
        )

        chamado = criar_chamado(payload)

        # Notifica equipe de TI via WebSocket
        await notificar_novo_chamado(chamado, user.name)

        return RedirectResponse(url="/colaborador/", status_code=303)

    except Exception as e:
        setores = listar_setores()
        return templates.TemplateResponse(
            request=request,
            name="colaborador/novo_chamado.html",
            context={
                "request": request,
                "user": user,
                "setores": setores,
                "erro": str(e),
                "dados": {
                    "setor_loja": setor_loja,
                    "assunto": assunto,
                    "descricao": descricao,
                }
            }
        )


# ── CHAT ───────────────────────────────────────────────────────────────────────

@router.get("/chat/{chamado_id}", response_class=HTMLResponse, name="colaborador_chat")
async def colaborador_chat(request: Request, chamado_id: str):
    user = request.state.user
    if user.is_admin:
        return RedirectResponse(url=f"/chamados/{chamado_id}/chat", status_code=303)

    chamado = buscar_chamado(chamado_id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if chamado.usuario_id != user.id:
        raise HTTPException(status_code=403, detail="Sem permissão para este chamado")

    # Carrega histórico de mensagens
    chat_data = _load_chat()
    mensagens = chat_data.get(chamado_id, [])

    # Marca como lido
    mark_chat_read(user.id, chamado_id)

    return templates.TemplateResponse(
        request=request,
        name="colaborador/chat.html",
        context={
            "request": request,
            "user": user,
            "chamado": chamado,
            "mensagens": mensagens,
        }
    )
