# routers/reservas.py — Rotas de Reserva de Salas
from fastapi import APIRouter, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import date, datetime

from crud.crud_reservas import (
    listar_reservas, buscar_reserva, criar_reserva,
    atualizar_reserva, excluir_reserva, validar_reserva
)
from crud.users import get_all_users, get_user_by_id
from models.reserva import ReservaCreate, ReservaUpdate, StatusReserva, SalaOpcoes

router = APIRouter(prefix="/reservas", tags=["Reservas"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse, name="listar_reservas")
async def pg_listar_reservas(
    request: Request,
    sala: Optional[str] = None,
    data_filtro: Optional[date] = None,
    status: Optional[str] = None,
    busca: Optional[str] = None
):
    user = request.state.user
    
    # Listagem de reservas aplicando filtros
    reservas = listar_reservas(
        sala=sala,
        data_filtro=data_filtro,
        status=status,
        pesquisa=busca
    )
    
    users = get_all_users()
    user_map = {u.id: u.name for u in users}

    # Definir cores para indicadores visuais de salas e status
    cores_salas = {
        SalaOpcoes.REUNIAO.value: "bg-indigo-500/20 text-indigo-300 border-indigo-500/40",
        SalaOpcoes.TREINAMENTO.value: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
    }
    
    cores_status = {
        StatusReserva.AGENDADA.value: "bg-blue-500/20 text-blue-300 border-blue-500/40",
        StatusReserva.CANCELADA.value: "bg-red-500/20 text-red-300 border-red-500/40",
        StatusReserva.CONCLUIDA.value: "bg-green-500/20 text-green-300 border-green-500/40",
    }

    # Determinar se a sala está ocupadaAGORA
    agora = datetime.now()
    hoje_str = agora.date().isoformat()
    agora_min = agora.hour * 60 + agora.minute
    
    sala_status = {
        SalaOpcoes.REUNIAO.value: "Livre",
        SalaOpcoes.TREINAMENTO.value: "Livre"
    }
    
    # Verifica reservas de hoje agendadas que coincidem com a hora atual
    for r in listar_reservas(data_filtro=agora.date(), status=StatusReserva.AGENDADA.value):
        from crud.crud_reservas import time_to_minutes
        r_start = time_to_minutes(r.hora_inicio)
        r_end = time_to_minutes(r.hora_fim)
        if r_start <= agora_min < r_end:
            sala_status[r.sala.value] = "Ocupada"

    return templates.TemplateResponse(
        request=request,
        name="reservas/dashboard.html",
        context={
            "request": request,
            "user": user,
            "reservas": reservas,
            "user_map": user_map,
            "salas": [s.value for s in SalaOpcoes],
            "status_opcoes": [st.value for st in StatusReserva],
            "cores_salas": cores_salas,
            "cores_status": cores_status,
            "sala_status": sala_status,
            "filtro_sala": sala or "",
            "filtro_data": data_filtro.isoformat() if data_filtro else "",
            "filtro_status": status or "",
            "busca": busca or "",
            "hoje": hoje_str
        }
    )


@router.get("/events", response_class=JSONResponse)
async def get_events(
    sala: Optional[str] = None,
    status: Optional[str] = None
):
    """Retorna as reservas formatadas para o FullCalendar."""
    reservas = listar_reservas(sala=sala, status=status)
    events = []
    
    cores_salas_calendar = {
        SalaOpcoes.REUNIAO.value: "#6366f1",      # Indigo
        SalaOpcoes.TREINAMENTO.value: "#10b981",  # Emerald
    }

    users = get_all_users()
    user_map = {u.id: u.name for u in users}

    for r in reservas:
        # Pega a cor com base na sala
        color = cores_salas_calendar.get(r.sala.value, "#3b82f6")
        if r.status == StatusReserva.CANCELADA:
            color = "#ef4444"  # Red para cancelados
        elif r.status == StatusReserva.CONCLUIDA:
            color = "#22c55e"  # Green para concluídos

        events.append({
            "id": r.id,
            "title": f"[{r.sala.value}] {r.titulo}",
            "start": f"{r.data.isoformat()}T{r.hora_inicio}:00",
            "end": f"{r.data.isoformat()}T{r.hora_fim}:00",
            "color": color,
            "extendedProps": {
                "sala": r.sala.value,
                "status": r.status.value,
                "descricao": r.descricao or "",
                "solicitante": user_map.get(r.usuario_id, "Desconhecido"),
                "participantes": r.participantes or "",
                "observacoes": r.observacoes or "",
                "usuario_id": r.usuario_id
            }
        })
    return events


@router.post("/nova")
async def post_nova_reserva(
    request: Request,
    sala: str = Form(...),
    titulo: str = Form(...),
    descricao: Optional[str] = Form(None),
    data: str = Form(...),
    hora_inicio: str = Form(...),
    hora_fim: str = Form(...),
    participantes: Optional[str] = Form(None),
    observacoes: Optional[str] = Form(None)
):
    user = request.state.user
    
    try:
        data_obj = date.fromisoformat(data)
    except ValueError:
        raise HTTPException(status_code=400, detail="Data inválida.")

    payload = ReservaCreate(
        sala=SalaOpcoes(sala),
        titulo=titulo,
        descricao=descricao,
        data=data_obj,
        hora_inicio=hora_inicio,
        hora_fim=hora_fim,
        participantes=participantes,
        observacoes=observacoes
    )

    ok, erro = validar_reserva(payload)
    if not ok:
        # Se vier via HTMX ou AJAX, retorna JSON
        if request.headers.get("HX-Request") or request.headers.get("Accept") == "application/json":
            return JSONResponse(status_code=400, content={"status": "erro", "msg": erro})
        # Caso contrário, redireciona com query parameter de erro ou lança HTTPException
        raise HTTPException(status_code=400, detail=erro)

    criar_reserva(payload, user.id)
    
    if request.headers.get("HX-Request"):
        return JSONResponse(content={"status": "ok"})
    return RedirectResponse(url="/reservas/", status_code=303)


@router.post("/editar/{reserva_id}")
async def post_editar_reserva(
    request: Request,
    reserva_id: str,
    sala: str = Form(...),
    titulo: str = Form(...),
    descricao: Optional[str] = Form(None),
    data: str = Form(...),
    hora_inicio: str = Form(...),
    hora_fim: str = Form(...),
    participantes: Optional[str] = Form(None),
    observacoes: Optional[str] = Form(None),
    status: str = Form(...)
):
    user = request.state.user
    reserva_existente = buscar_reserva(reserva_id)
    if not reserva_existente:
        raise HTTPException(status_code=404, detail="Reserva não encontrada.")

    # Regra: Criador ou Administrador pode editar
    if not user.is_admin and reserva_existente.usuario_id != user.id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar esta reserva.")

    try:
        data_obj = date.fromisoformat(data)
    except ValueError:
        raise HTTPException(status_code=400, detail="Data inválida.")

    payload_valida = ReservaCreate(
        sala=SalaOpcoes(sala),
        titulo=titulo,
        descricao=descricao,
        data=data_obj,
        hora_inicio=hora_inicio,
        hora_fim=hora_fim,
        participantes=participantes,
        observacoes=observacoes
    )

    # Validamos as regras de conflito, ignorando o próprio ID da reserva sendo editada
    ok, erro = validar_reserva(payload_valida, ignorar_id=reserva_id)
    if not ok:
        return JSONResponse(status_code=400, content={"status": "erro", "msg": erro})

    payload_update = ReservaUpdate(
        sala=SalaOpcoes(sala),
        titulo=titulo,
        descricao=descricao,
        data=data_obj,
        hora_inicio=hora_inicio,
        hora_fim=hora_fim,
        participantes=participantes,
        observacoes=observacoes,
        status=StatusReserva(status)
    )

    atualizar_reserva(reserva_id, payload_update)
    return JSONResponse(content={"status": "ok"})


@router.post("/cancelar/{reserva_id}")
async def post_cancelar_reserva(request: Request, reserva_id: str):
    user = request.state.user
    reserva = buscar_reserva(reserva_id)
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva não encontrada.")

    # Regra: Criador ou Administrador pode cancelar
    if not user.is_admin and reserva.usuario_id != user.id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para cancelar esta reserva.")

    payload = ReservaUpdate(status=StatusReserva.CANCELADA)
    atualizar_reserva(reserva_id, payload)
    
    return JSONResponse(content={"status": "ok"})


@router.post("/excluir/{reserva_id}")
async def post_excluir_reserva(request: Request, reserva_id: str):
    user = request.state.user
    reserva = buscar_reserva(reserva_id)
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva não encontrada.")

    # Regra: Apenas Administrador pode excluir qualquer reserva
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Apenas administradores podem excluir reservas.")

    excluir_reserva(reserva_id)
    return JSONResponse(content={"status": "ok"})
