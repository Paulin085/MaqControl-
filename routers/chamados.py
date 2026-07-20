from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import pandas as pd
from io import BytesIO
from datetime import datetime, date
import os
import shutil

from crud.crud_chamados import listar_chamados, buscar_chamado, criar_chamado, atualizar_chamado, deletar_chamado
from crud import listar_setores
from models.chamado import ChamadoCreate, ChamadoUpdate, Dificuldade, StatusChamado, TipoChamado
from routers.desktop_api import get_unread_count

router = APIRouter(prefix="/chamados", tags=["Chamados"])
templates = Jinja2Templates(directory="templates")

# Pasta para uploads
UPLOAD_DIR = "static/uploads/chamados"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/", response_class=HTMLResponse, name="chamados_dashboard")
async def pg_chamados_dashboard(
    request: Request,
    busca: Optional[str] = None,
    status: Optional[str] = None,
    tipo: Optional[str] = None,
    dificuldade: Optional[str] = None
):
    chamados = listar_chamados()
    setores = listar_setores()
    user = request.state.user
    
    if not user.is_admin:
        chamados = [c for c in chamados if c.usuario_id == user.id]
    
    # Dashboard mostra:
    # 1. Chamados em Fila ou Em Andamento (independente da data)
    # 2. Chamados Concluídos apenas se forem de HOJE
    hoje = date.today()
    chamados_dashboard = [
        c for c in chamados 
        if c.status in [StatusChamado.FILA, StatusChamado.EM_ANDAMENTO] 
        or (c.status == StatusChamado.CONCLUIDO and c.data_registro.date() == hoje)
    ]

    # Indicadores
    total_dashboard = len(chamados_dashboard)
    em_aberto = len([c for c in chamados_dashboard if c.status != StatusChamado.CONCLUIDO])
    concluidos_hoje = len([c for c in chamados_dashboard if c.status == StatusChamado.CONCLUIDO and c.data_registro.date() == hoje])
    
    # Filtros
    if busca:
        busca = busca.lower()
        chamados_dashboard = [c for c in chamados_dashboard if 
                              (c.solicitante and busca in c.solicitante.lower()) or 
                              (c.setor_loja and busca in c.setor_loja.lower()) or
                              (c.titulo and busca in c.titulo.lower())]
    if status:
        chamados_dashboard = [c for c in chamados_dashboard if c.status == status]
    if tipo:
        chamados_dashboard = [c for c in chamados_dashboard if c.tipo == tipo]
    if dificuldade:
        chamados_dashboard = [c for c in chamados_dashboard if c.dificuldade == dificuldade]

    # Ordenar por data
    chamados_dashboard.sort(key=lambda x: x.data_registro, reverse=True)

    # Agrupar por status
    grupos = {
        "Fila": [c for c in chamados_dashboard if c.status == StatusChamado.FILA],
        "Em Andamento": [c for c in chamados_dashboard if c.status == StatusChamado.EM_ANDAMENTO],
        "Concluído": [c for c in chamados_dashboard if c.status == StatusChamado.CONCLUIDO]
    }

    # Contagem de mensagens não lidas por chamado (para botão de chat no card)
    unread = {}
    if user.is_admin:
        unread = {
            c.id: get_unread_count(user.id, c.id, user_is_admin=True)
            for c in chamados_dashboard
        }

    return templates.TemplateResponse(
        request=request,
        name="chamados/dashboard.html",
        context={
            "request": request,
            "chamados": chamados_dashboard,
            "grupos": grupos,
            "setores": setores,
            "unread": unread,
            "indicadores": {
                "total": total_dashboard,
                "em_aberto": em_aberto,
                "concluidos_hoje": concluidos_hoje
            },
            "filtros": {
                "busca": busca,
                "status": status,
                "tipo": tipo,
                "dificuldade": dificuldade
            },
            "status_options": [s.value for s in StatusChamado],
            "tipo_options": [t.value for t in TipoChamado],
            "dificuldade_options": [d.value for d in Dificuldade],
            "apenas_hoje": True
        }
    )

@router.get("/lista", response_class=HTMLResponse, name="chamados_lista")
async def pg_chamados_lista(
    request: Request,
    busca: Optional[str] = None,
    status: Optional[str] = None,
    tipo: Optional[str] = None,
    dificuldade: Optional[str] = None
):
    chamados = listar_chamados()
    setores = listar_setores()
    user = request.state.user
    
    if not user.is_admin:
        chamados = [c for c in chamados if c.usuario_id == user.id]
    
    # Filtros
    if busca:
        busca = busca.lower()
        chamados = [c for c in chamados if 
                    (c.solicitante and busca in c.solicitante.lower()) or 
                    (c.setor_loja and busca in c.setor_loja.lower()) or
                    (c.titulo and busca in c.titulo.lower())]
    if status:
        chamados = [c for c in chamados if c.status == status]
    if tipo:
        chamados = [c for c in chamados if c.tipo == tipo]
    if dificuldade:
        chamados = [c for c in chamados if c.dificuldade == dificuldade]

    # Ordenar por data (mais recentes primeiro)
    chamados.sort(key=lambda x: x.data_registro, reverse=True)

    return templates.TemplateResponse(
        request=request,
        name="chamados/lista.html",
        context={
            "request": request,
            "chamados": chamados,
            "setores": setores,
            "filtros": {
                "busca": busca,
                "status": status,
                "tipo": tipo,
                "dificuldade": dificuldade
            },
            "status_options": [s.value for s in StatusChamado],
            "tipo_options": [t.value for t in TipoChamado],
            "dificuldade_options": [d.value for d in Dificuldade]
        }
    )

@router.get("/novo", response_class=HTMLResponse, name="form_novo_chamado")
async def pg_form_novo_chamado(request: Request):
    setores = listar_setores()
    return templates.TemplateResponse(
        request=request,
        name="chamados/form.html",
        context={
            "request": request,
            "setores": setores,
            "hoje": datetime.now().strftime("%Y-%m-%dT%H:%M"),
            "status_options": [s.value for s in StatusChamado],
            "tipo_options": [t.value for t in TipoChamado],
            "dificuldade_options": [d.value for d in Dificuldade]
        }
    )

@router.post("/novo", name="criar_chamado_post")
async def pg_criar_chamado(
    request: Request,
    setor_loja: Optional[str] = Form(None),
    solicitante: Optional[str] = Form(None),
    titulo: Optional[str] = Form(None),
    tipo: str = Form(TipoChamado.CHAMADO.value),
    dificuldade: str = Form(...),
    descricao: str = Form(...),
    status: str = Form(StatusChamado.FILA.value),
    resolucao: Optional[str] = Form(None),
    data_registro: str = Form(...),
    anexo: Optional[UploadFile] = File(None)
):
    try:
        anexo_path = None
        if anexo and anexo.filename:
            file_ext = os.path.splitext(anexo.filename)[1]
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{anexo.filename}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(anexo.file, buffer)
            anexo_path = f"/static/uploads/chamados/{filename}"

        payload = ChamadoCreate(
            setor_loja=setor_loja,
            solicitante=solicitante,
            titulo=titulo,
            tipo=TipoChamado(tipo),
            dificuldade=Dificuldade(dificuldade),
            descricao=descricao,
            status=StatusChamado(status),
            resolucao=resolucao,
            data_registro=datetime.fromisoformat(data_registro),
            anexo_path=anexo_path,
            usuario_id=request.state.user.id
        )
        criar_chamado(payload)
        return RedirectResponse(url="/chamados/", status_code=303)
    except Exception as e:
        setores = listar_setores()
        return templates.TemplateResponse(
            request=request,
            name="chamados/form.html",
            context={
                "request": request,
                "setores": setores,
                "erro": str(e),
                "hoje": data_registro,
                "status_options": [s.value for s in StatusChamado],
                "tipo_options": [t.value for t in TipoChamado],
                "dificuldade_options": [d.value for d in Dificuldade]
            }
        )

@router.get("/exportar", name="exportar_chamados")
async def pg_exportar_chamados(
    request: Request,
    busca: Optional[str] = None,
    status: Optional[str] = None,
    tipo: Optional[str] = None,
    dificuldade: Optional[str] = None
):
    chamados = listar_chamados()
    user = request.state.user
    
    if not user.is_admin:
        chamados = [c for c in chamados if c.usuario_id == user.id]
    
    if busca:
        busca = busca.lower()
        chamados = [c for c in chamados if 
                    (c.solicitante and busca in c.solicitante.lower()) or 
                    (c.setor_loja and busca in c.setor_loja.lower()) or
                    (c.titulo and busca in c.titulo.lower())]
    if status:
        chamados = [c for c in chamados if c.status == status]
    if tipo:
        chamados = [c for c in chamados if c.tipo == tipo]
    if dificuldade:
        chamados = [c for c in chamados if c.dificuldade == dificuldade]

    # Criar DataFrame
    data = []
    for c in chamados:
        data.append({
            "ID": c.id,
            "Título": c.titulo or "",
            "Setor/Loja": c.setor_loja or "",
            "Solicitante": c.solicitante or "",
            "Tipo": c.tipo.value,
            "Nível de Atenção": c.dificuldade.value,
            "Status": c.status.value,
            "Data Registro": c.data_registro.strftime("%d/%m/%Y %H:%M"),
            "Descrição": c.descricao,
            "Resolução": c.resolucao or ""
        })
    
    df = pd.DataFrame(data)
    
    # Gerar Excel em memória
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Chamados')
    
    output.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="chamados.xlsx"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@router.get("/{id}/editar", response_class=HTMLResponse, name="form_editar_chamado")
async def pg_form_editar_chamado(request: Request, id: str):
    chamado = buscar_chamado(id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    user = request.state.user
    if not user.is_admin and chamado.usuario_id != user.id:
        raise HTTPException(status_code=403, detail="Sem permissão para acessar este chamado")
    
    setores = listar_setores()
    return templates.TemplateResponse(
        request=request,
        name="chamados/form.html",
        context={
            "request": request,
            "chamado": chamado,
            "setores": setores,
            "hoje": chamado.data_registro.strftime("%Y-%m-%dT%H:%M"),
            "status_options": [s.value for s in StatusChamado],
            "tipo_options": [t.value for t in TipoChamado],
            "dificuldade_options": [d.value for d in Dificuldade]
        }
    )

@router.post("/{id}/editar", name="editar_chamado_post")
async def pg_editar_chamado(
    request: Request,
    id: str,
    setor_loja: Optional[str] = Form(None),
    solicitante: Optional[str] = Form(None),
    titulo: Optional[str] = Form(None),
    tipo: str = Form(TipoChamado.CHAMADO.value),
    dificuldade: str = Form(...),
    descricao: str = Form(...),
    resolucao: Optional[str] = Form(None),
    status: str = Form(...),
    data_registro: str = Form(...),
    anexo: Optional[UploadFile] = File(None)
):
    try:
        chamado_atual = buscar_chamado(id)
        if not chamado_atual:
            raise HTTPException(status_code=404, detail="Chamado não encontrado")

        user = request.state.user
        if not user.is_admin and chamado_atual.usuario_id != user.id:
            raise HTTPException(status_code=403, detail="Sem permissão para alterar este chamado")

        anexo_path = chamado_atual.anexo_path
        if anexo and anexo.filename:
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{anexo.filename}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(anexo.file, buffer)
            anexo_path = f"/static/uploads/chamados/{filename}"

        payload = ChamadoUpdate(
            setor_loja=setor_loja,
            solicitante=solicitante,
            titulo=titulo,
            tipo=TipoChamado(tipo),
            dificuldade=Dificuldade(dificuldade),
            descricao=descricao,
            resolucao=resolucao,
            status=StatusChamado(status),
            anexo_path=anexo_path
        )
        # Note: data_registro update might need a new model field or handling
        # For now, let's keep it simple as ChamadoUpdate doesn't have data_registro
        
        chamado_atualizado = atualizar_chamado(id, payload)
        if chamado_atualizado:
            from routers.desktop_api import notificar_atualizacao_chamado
            await notificar_atualizacao_chamado(chamado_atualizado)
        return RedirectResponse(url="/chamados/", status_code=303)
    except Exception as e:
        setores = listar_setores()
        chamado = buscar_chamado(id)
        return templates.TemplateResponse(
            request=request,
            name="chamados/form.html",
            context={
                "request": request,
                "chamado": chamado,
                "setores": setores,
                "erro": str(e),
                "hoje": data_registro,
                "status_options": [s.value for s in StatusChamado],
                "tipo_options": [t.value for t in TipoChamado],
                "dificuldade_options": [d.value for d in Dificuldade]
            }
        )

@router.post("/avancar", name="avancar_chamado_post")
async def pg_avancar_chamado(request: Request, id: str):
    chamado = buscar_chamado(id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    user = request.state.user
    if not user.is_admin and chamado.usuario_id != user.id:
        raise HTTPException(status_code=403, detail="Sem permissão para alterar este chamado")
    
    # Lógica de progressão
    novo_status = chamado.status
    if chamado.status == StatusChamado.FILA:
        novo_status = StatusChamado.EM_ANDAMENTO
    elif chamado.status == StatusChamado.EM_ANDAMENTO:
        novo_status = StatusChamado.CONCLUIDO
    
    if novo_status != chamado.status:
        payload = ChamadoUpdate(status=novo_status)
        chamado_atualizado = atualizar_chamado(id, payload)
        if chamado_atualizado:
            from routers.desktop_api import notificar_atualizacao_chamado
            await notificar_atualizacao_chamado(chamado_atualizado)

    return RedirectResponse(url="/chamados/", status_code=303)

@router.post("/{id}/deletar", name="deletar_chamado_post")
async def pg_deletar_chamado(request: Request, id: str):
    chamado = buscar_chamado(id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
        
    user = request.state.user
    if not user.is_admin and chamado.usuario_id != user.id:
        raise HTTPException(status_code=403, detail="Sem permissão para excluir este chamado")
        
    deletar_chamado(id)
    return RedirectResponse(url="/chamados/", status_code=303)


@router.get("/{id}/chat", response_class=HTMLResponse, name="chamado_chat_it")
async def pg_chamado_chat_it(request: Request, id: str):
    """Redireciona para o chat centralizado."""
    return RedirectResponse(url=f"/chat?c={id}", status_code=303)
