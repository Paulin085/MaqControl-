# routers/maquinas.py — CRUD de Máquinas
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import date

from crud import (
    listar_maquinas, buscar_maquina, criar_maquina,
    atualizar_maquina, deletar_maquina, listar_setores
)
from crud.crud_manutencoes import listar_manutencoes_da_maquina
from models.maquina import MaquinaCreate, MaquinaUpdate, TipoMaquina

router = APIRouter(prefix="/maquinas", tags=["Máquinas"])
templates = Jinja2Templates(directory="templates")


@router.get("/",
        name="listar_maquinas")
async def pg_listar_maquinas(
    request: Request,
    setor_id: Optional[str] = None,
    tipo: Optional[str] = None,
    status: Optional[str] = None,
    busca: Optional[str] = None,
):
    maquinas = listar_maquinas(setor_id=setor_id, tipo=tipo, status=status)
    setores  = listar_setores()
    setor_map = {s.id: s.nome for s in setores}

    # Busca por nome/IP/hostname
    if busca:
        busca_lower = busca.lower()
        maquinas = [
            m for m in maquinas
            if busca_lower in m.nome.lower()
            or (m.ip and busca_lower in m.ip)
            or (m.anydesk and busca_lower in m.anydesk)
        ]

    return templates.TemplateResponse(request=request,
        name="maquinas/lista.html",
        context={
        "request": request,
        "maquinas": maquinas,
        "setores": setores,
        "setor_map": setor_map,
        "filtro_setor": setor_id,
        "filtro_tipo": tipo,
        "filtro_status": status,
        "busca": busca or "",
        "tipos": [t.value for t in TipoMaquina],
    })


@router.get("/nova",
        name="form_nova_maquina")
async def pg_form_nova(request: Request):
    setores = listar_setores()
    return templates.TemplateResponse(request=request,
        name="maquinas/form.html",
        context={
        "request": request,
        "maquina": None,
        "setores": setores,
        "tipos": [t.value for t in TipoMaquina],
        "titulo": "Nova Máquina",
    })


@router.post("/nova",
        name="criar_maquina_post")
async def pg_criar_maquina(
    request: Request,
    nome: str = Form(...),
    tipo: str = Form(...),
    setor_id: str = Form(...),
    ip: Optional[str] = Form(None),
    anydesk: Optional[str] = Form(None),
    processador: Optional[str] = Form(None),
    memoria_ram: Optional[str] = Form(None),
    armazenamento_tipo: Optional[str] = Form(None),
    armazenamento_capacidade: Optional[str] = Form(None),
    data_aquisicao: Optional[str] = Form(None),
    observacoes: Optional[str] = Form(None),
    intervalo_manutencao_dias: Optional[int] = Form(None),
):
    try:
        data_aq = date.fromisoformat(data_aquisicao) if data_aquisicao else None
        payload = MaquinaCreate(
            nome=nome, tipo=tipo, setor_id=setor_id,
            ip=ip or None, anydesk=anydesk or None,
            processador=processador or None,
            memoria_ram=memoria_ram or None,
            armazenamento_tipo=armazenamento_tipo or None,
            armazenamento_capacidade=armazenamento_capacidade or None,
            data_aquisicao=data_aq,
            observacoes=observacoes or None,
            intervalo_manutencao_dias=intervalo_manutencao_dias,
        )
        maquina = criar_maquina(payload)
        return RedirectResponse(url=f"/maquinas/{maquina.id}",
        status_code=303)
    except Exception as e:
        setores = listar_setores()
        return templates.TemplateResponse(request=request,
        name="maquinas/form.html",
        context={
            "request": request, "maquina": None, "setores": setores,
            "tipos": [t.value for t in TipoMaquina],
            "titulo": "Nova Máquina", "erro": str(e),
        })


@router.get("/{maquina_id}",
        name="detalhe_maquina")
async def pg_detalhe_maquina(request: Request, maquina_id: str):
    maquina = buscar_maquina(maquina_id)
    if not maquina:
        raise HTTPException(status_code=404, detail="Máquina não encontrada")

    setores = listar_setores()
    setor_map = {s.id: s.nome for s in setores}
    historico = listar_manutencoes_da_maquina(maquina_id)

    # Intervalo efetivo (personalizado ou do setor)
    intervalo_efetivo = maquina.intervalo_manutencao_dias
    if not intervalo_efetivo:
        setor = next((s for s in setores if s.id == maquina.setor_id), None)
        if setor:
            intervalo_efetivo = setor.intervalo_manutencao_dias

    return templates.TemplateResponse(request=request,
        name="maquinas/detalhe.html",
        context={
        "request": request,
        "maquina": maquina,
        "setor_nome": setor_map.get(maquina.setor_id, "—"),
        "historico": historico,
        "intervalo_efetivo": intervalo_efetivo,
        "hoje": date.today(),
    })


@router.get("/{maquina_id}/editar",
        name="form_editar_maquina")
async def pg_form_editar(request: Request, maquina_id: str):
    maquina = buscar_maquina(maquina_id)
    if not maquina:
        raise HTTPException(status_code=404, detail="Máquina não encontrada")
    setores = listar_setores()
    return templates.TemplateResponse(request=request,
        name="maquinas/form.html",
        context={
        "request": request,
        "maquina": maquina,
        "setores": setores,
        "tipos": [t.value for t in TipoMaquina],
        "titulo": "Editar Máquina",
    })


@router.post("/{maquina_id}/editar",
        name="editar_maquina_post")
async def pg_editar_maquina(
    request: Request,
    maquina_id: str,
    nome: str = Form(...),
    tipo: str = Form(...),
    setor_id: str = Form(...),
    ip: Optional[str] = Form(None),
    anydesk: Optional[str] = Form(None),
    processador: Optional[str] = Form(None),
    memoria_ram: Optional[str] = Form(None),
    armazenamento_tipo: Optional[str] = Form(None),
    armazenamento_capacidade: Optional[str] = Form(None),
    data_aquisicao: Optional[str] = Form(None),
    observacoes: Optional[str] = Form(None),
    intervalo_manutencao_dias: Optional[int] = Form(None),
):
    data_aq = date.fromisoformat(data_aquisicao) if data_aquisicao else None
    payload = MaquinaUpdate(
        nome=nome, tipo=tipo, setor_id=setor_id,
        ip=ip or None, anydesk=anydesk or None,
        processador=processador or None, memoria_ram=memoria_ram or None,
        armazenamento_tipo=armazenamento_tipo or None,
        armazenamento_capacidade=armazenamento_capacidade or None,
        data_aquisicao=data_aq,
        observacoes=observacoes or None,
        intervalo_manutencao_dias=intervalo_manutencao_dias,
    )
    resultado = atualizar_maquina(maquina_id, payload)
    if not resultado:
        raise HTTPException(status_code=404, detail="Máquina não encontrada")
    return RedirectResponse(url=f"/maquinas/{maquina_id}",
        status_code=303)


@router.post("/{maquina_id}/deletar",
        name="deletar_maquina_post")
async def pg_deletar_maquina(maquina_id: str):
    if not deletar_maquina(maquina_id):
        raise HTTPException(status_code=404, detail="Máquina não encontrada")
    return RedirectResponse(url="/maquinas/",
        status_code=303)
