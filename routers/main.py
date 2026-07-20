# main.py — Ponto de entrada do MaqControl
# Execute com: python main.py  OU  uvicorn main:app --reload

import uvicorn
from fastapi import FastAPI, Request, Query
from fastapi.staticfiles import StaticFiles
from typing import Optional
from pathlib import Path
from routers import dashboard, maquinas, setores, manutencoes, relatorios, auth, chamados, admin, desktop_api

# Garante que os diretórios existam
for d in ["data", "static/css", "static/js", "templates"]:
    Path(d).mkdir(parents=True, exist_ok=True)

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MaqControl",
    description="Sistema de Controle de Máquinas da Empresa",
    version="1.0.0",
    docs_url="/api/docs",
)

app.mount("/static", StaticFiles(directory="static"),
        name="static")

# ── Routers ──────────────────────────────────────────────────────────────────
from routers import dashboard, maquinas, setores, manutencoes, relatorios, auth, chamados, admin
app.include_router(dashboard.router)
app.include_router(maquinas.router)
app.include_router(setores.router)
app.include_router(manutencoes.router)
app.include_router(relatorios.router)
app.include_router(auth.router)
app.include_router(chamados.router)
app.include_router(admin.router)
app.include_router(desktop_api.router)
# ── Tratamento de erros e Segurança ────────────────────────────────────────────
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
templates = Jinja2Templates(directory="templates")

from crud.users import get_user_by_id

@app.middleware("http")
async def verify_authentication(request: Request, call_next):
    # Rotas públicas que não exigem login
    rotas_publicas = [
        "/login", 
        "/ping", 
        "/openapi.json", 
        "/api/docs", 
        "/logout",
        "/api/desktop/auth"  
    ]

    if request.url.path.startswith("/static"):
        return await call_next(request)
        
    if request.url.path in rotas_publicas:
        return await call_next(request)
    
    # WebSocket também não precisa de middleware
    if request.url.path.startswith("/api/desktop/ws"):
        return await call_next(request)

    # Checa o cookie
    session_token = request.cookies.get("maqcontrol_auth")
    if not session_token:
        return RedirectResponse(url="/login", status_code=303)
        
    user = get_user_by_id(session_token)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    request.state.user = user

    # Renova o cookie por mais 30 minutos (Inatividade)
    response = await call_next(request)
    response.set_cookie(key="maqcontrol_auth", value=session_token, httponly=True, max_age=1800)
    return response

@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse(request=request,
        name="erros/404.html",
        context={"request": request},
        status_code=404
    )

@app.exception_handler(500)
async def server_error(request: Request, exc):
    return templates.TemplateResponse(request=request,
        name="erros/500.html",
        context={"request": request},
        status_code=500
    )

# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/ping", include_in_schema=False)
def ping():
    return {"status": "ok", "sistema": "MaqControl v1.0"}


from crud.crud_chamados import buscar_chamado, atualizar_chamado
from models.chamado import StatusChamado, ChamadoUpdate


@app.post("/chamados/avancar-emergencial", include_in_schema=False)
async def avancar_chamado_emergencial(request: Request, id: str = Query(...), resolucao: Optional[str] = Query(None)):
    chamado = buscar_chamado(id)
    if not chamado:
        return {"status": "erro", "msg": "Chamado não encontrado"}
        
    user = request.state.user
    if not user.is_admin and chamado.usuario_id != user.id:
        return {"status": "erro", "msg": "Sem permissão"}
    
    status_atual = chamado.status
    novo_status = status_atual
    
    if status_atual == StatusChamado.FILA:
        novo_status = StatusChamado.EM_ANDAMENTO
    elif status_atual == StatusChamado.EM_ANDAMENTO:
        novo_status = StatusChamado.CONCLUIDO
    
    if novo_status != status_atual:
        update_data = {"status": novo_status}
        if resolucao:
            update_data["resolucao"] = resolucao
            
        payload = ChamadoUpdate(**update_data)
        updated = atualizar_chamado(id, payload)
        if not updated:
            return {"status": "erro", "msg": "Falha ao atualizar chamado no banco"}

        from routers.desktop_api import notificar_atualizacao_chamado
        await notificar_atualizacao_chamado(updated)

    return {"status": "ok", "id": id, "novo_status": novo_status}

@app.post("/chamados/voltar-emergencial", include_in_schema=False)
async def voltar_chamado_emergencial(request: Request, id: str = Query(...)):
    chamado = buscar_chamado(id)
    if not chamado:
        return {"status": "erro", "msg": "Chamado não encontrado"}
        
    user = request.state.user
    if not user.is_admin and chamado.usuario_id != user.id:
        return {"status": "erro", "msg": "Sem permissão"}
    
    # Força a volta direta para a Fila conforme solicitado
    payload = ChamadoUpdate(status=StatusChamado.FILA)
    updated = atualizar_chamado(id, payload)

    if updated:
        from routers.desktop_api import notificar_atualizacao_chamado
        await notificar_atualizacao_chamado(updated)

    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
