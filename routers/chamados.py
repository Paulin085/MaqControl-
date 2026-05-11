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
from models.chamado import ChamadoCreate, ChamadoUpdate, Dificuldade, StatusChamado

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
    dificuldade: Optional[str] = None
):
    chamados = listar_chamados()
    setores = listar_setores()
    
    # Indicadores
    total = len(chamados)
    em_aberto = len([c for c in chamados if c.status != StatusChamado.CONCLUIDO])
    concluidos_hoje = len([c for c in chamados if c.status == StatusChamado.CONCLUIDO and c.data_registro.date() == date.today()])
    
    # Filtros
    if busca:
        busca = busca.lower()
        chamados = [c for c in chamados if busca in c.solicitante.lower() or busca in c.setor_loja.lower()]
    if status:
        chamados = [c for c in chamados if c.status == status]
    if dificuldade:
        chamados = [c for c in chamados if c.dificuldade == dificuldade]

    # Ordenar por data (mais recentes primeiro)
    chamados.sort(key=lambda x: x.data_registro, reverse=True)

    # Agrupar por status
    grupos = {
        "Fila": [c for c in chamados if c.status == StatusChamado.FILA],
        "Em Andamento": [c for c in chamados if c.status == StatusChamado.EM_ANDAMENTO],
        "Concluído": [c for c in chamados if c.status == StatusChamado.CONCLUIDO]
    }

    return templates.TemplateResponse(
        request=request,
        name="chamados/dashboard.html",
        context={
            "request": request,
            "chamados": chamados,
            "grupos": grupos,
            "setores": setores,
            "indicadores": {
                "total": total,
                "em_aberto": em_aberto,
                "concluidos_hoje": concluidos_hoje
            },
            "filtros": {
                "busca": busca,
                "status": status,
                "dificuldade": dificuldade
            },
            "status_options": [s.value for s in StatusChamado],
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
            "dificuldade_options": [d.value for d in Dificuldade]
        }
    )

@router.post("/novo", name="criar_chamado_post")
async def pg_criar_chamado(
    request: Request,
    setor_loja: str = Form(...),
    solicitante: str = Form(...),
    dificuldade: str = Form(...),
    descricao: str = Form(...),
    status: str = Form(StatusChamado.FILA.value),
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
            dificuldade=Dificuldade(dificuldade),
            descricao=descricao,
            status=StatusChamado(status),
            data_registro=datetime.fromisoformat(data_registro),
            anexo_path=anexo_path
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
                "dificuldade_options": [d.value for d in Dificuldade]
            }
        )

@router.get("/exportar", name="exportar_chamados")
async def pg_exportar_chamados(
    busca: Optional[str] = None,
    status: Optional[str] = None,
    dificuldade: Optional[str] = None
):
    chamados = listar_chamados()
    
    if busca:
        busca = busca.lower()
        chamados = [c for c in chamados if busca in c.solicitante.lower() or busca in c.setor_loja.lower()]
    if status:
        chamados = [c for c in chamados if c.status == status]
    if dificuldade:
        chamados = [c for c in chamados if c.dificuldade == dificuldade]

    # Criar DataFrame
    data = []
    for c in chamados:
        data.append({
            "ID": c.id,
            "Setor/Loja": c.setor_loja,
            "Solicitante": c.solicitante,
            "Dificuldade": c.dificuldade.value,
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
            "dificuldade_options": [d.value for d in Dificuldade]
        }
    )

@router.post("/{id}/editar", name="editar_chamado_post")
async def pg_editar_chamado(
    request: Request,
    id: str,
    setor_loja: str = Form(...),
    solicitante: str = Form(...),
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
            dificuldade=Dificuldade(dificuldade),
            descricao=descricao,
            resolucao=resolucao,
            status=StatusChamado(status),
            anexo_path=anexo_path
        )
        # Note: data_registro update might need a new model field or handling
        # For now, let's keep it simple as ChamadoUpdate doesn't have data_registro
        
        atualizar_chamado(id, payload)
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
                "dificuldade_options": [d.value for d in Dificuldade]
            }
        )

@router.post("/avancar", name="avancar_chamado_post")
async def pg_avancar_chamado(id: str):
    chamado = buscar_chamado(id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    # Lógica de progressão
    novo_status = chamado.status
    if chamado.status == StatusChamado.FILA:
        novo_status = StatusChamado.EM_ANDAMENTO
    elif chamado.status == StatusChamado.EM_ANDAMENTO:
        novo_status = StatusChamado.CONCLUIDO
    
    if novo_status != chamado.status:
        payload = ChamadoUpdate(status=novo_status)
        atualizar_chamado(id, payload)
        
    return RedirectResponse(url="/chamados/", status_code=303)

@router.post("/{id}/deletar", name="deletar_chamado_post")
async def pg_deletar_chamado(id: str):
    deletar_chamado(id)
    return RedirectResponse(url="/chamados/", status_code=303)
