# routers/manutencoes.py — Registro de Manutenções
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import date

from crud import buscar_maquina
from crud.crud_manutencoes import criar_manutencao, deletar_manutencao
from models.manutencao import ManutencaoCreate

router = APIRouter(prefix="/manutencoes", tags=["Manutenções"])
templates = Jinja2Templates(directory="templates")

TIPOS_MANUTENCAO = ["Preventiva", "Corretiva", "Atualização", "Limpeza", "Outro"]


@router.get("/nova",
        name="form_nova_manutencao_global")
async def pg_form_manutencao_global(request: Request):
    from crud import listar_maquinas, listar_setores
    maquinas = listar_maquinas()
    setores = listar_setores()
    return templates.TemplateResponse(request=request,
        name="manutencoes/form_global.html",
        context={
        "request": request,
        "maquinas": maquinas,
        "setores": setores,
        "hoje": date.today().isoformat(),
        "tipos": TIPOS_MANUTENCAO,
    })


@router.post("/nova",
        name="criar_manutencao_global_post")
async def pg_criar_manutencao_global(
    request: Request,
    maquina_id: str = Form(...),
    data_manutencao: str = Form(...),
    descricao: str = Form(...),
    responsavel: str = Form(...),
    tipo: str = Form("Preventiva"),
    observacoes: Optional[str] = Form(None),
):
    from crud import listar_maquinas, listar_setores
    maquinas = listar_maquinas()
    setores = listar_setores()
    try:
        payload = ManutencaoCreate(
            maquina_id=maquina_id,
            data_manutencao=date.fromisoformat(data_manutencao),
            descricao=descricao,
            responsavel=responsavel,
            tipo=tipo,
            observacoes=observacoes or None,
        )
        criar_manutencao(payload)
        return RedirectResponse(url=f"/maquinas/{maquina_id}",
        status_code=303)
    except Exception as e:
        return templates.TemplateResponse(request=request,
        name="manutencoes/form_global.html",
        context={
            "request": request,
            "maquinas": maquinas,
            "setores": setores,
            "hoje": date.today().isoformat(),
            "tipos": TIPOS_MANUTENCAO,
            "erro": str(e),
        })


@router.get("/{maquina_id}/nova",
        name="form_nova_manutencao")
async def pg_form_manutencao(request: Request, maquina_id: str):
    maquina = buscar_maquina(maquina_id)
    if not maquina:
        raise HTTPException(status_code=404, detail="Máquina não encontrada")
    return templates.TemplateResponse(request=request,
        name="manutencoes/form.html",
        context={
        "request": request,
        "maquina": maquina,
        "hoje": date.today().isoformat(),
        "tipos": TIPOS_MANUTENCAO,
    })


@router.post("/{maquina_id}/nova",
        name="criar_manutencao_post")
async def pg_criar_manutencao(
    request: Request,
    maquina_id: str,
    data_manutencao: str = Form(...),
    descricao: str = Form(...),
    responsavel: str = Form(...),
    tipo: str = Form("Preventiva"),
    observacoes: Optional[str] = Form(None),
):
    maquina = buscar_maquina(maquina_id)
    if not maquina:
        raise HTTPException(status_code=404, detail="Máquina não encontrada")
    try:
        payload = ManutencaoCreate(
            maquina_id=maquina_id,
            data_manutencao=date.fromisoformat(data_manutencao),
            descricao=descricao,
            responsavel=responsavel,
            tipo=tipo,
            observacoes=observacoes or None,
        )
        criar_manutencao(payload)
        return RedirectResponse(url=f"/maquinas/{maquina_id}",
        status_code=303)
    except Exception as e:
        return templates.TemplateResponse(request=request,
        name="manutencoes/form.html",
        context={
            "request": request,
            "maquina": maquina,
            "hoje": date.today().isoformat(),
            "tipos": TIPOS_MANUTENCAO,
            "erro": str(e),
        })


@router.post("/{manutencao_id}/deletar",
        name="deletar_manutencao_post")
async def pg_deletar_manutencao(manutencao_id: str, maquina_id: str = Form(...)):
    deletar_manutencao(manutencao_id)
    return RedirectResponse(url=f"/maquinas/{maquina_id}",
        status_code=303)
