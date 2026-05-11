# main.py — Ponto de entrada do MaqControl
# Execute com: python main.py  OU  uvicorn main:app --reload

import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from pathlib import Path

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
from routers import dashboard, maquinas, setores, manutencoes, relatorios, auth, chamados
app.include_router(dashboard.router)
app.include_router(maquinas.router)
app.include_router(setores.router)
app.include_router(manutencoes.router)
app.include_router(relatorios.router)
app.include_router(auth.router)
app.include_router(chamados.router)

# ── Tratamento de erros e Segurança ────────────────────────────────────────────
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
templates = Jinja2Templates(directory="templates")

@app.middleware("http")
async def verify_authentication(request: Request, call_next):
    # Rotas públicas que não exigem login
    rotas_publicas = ["/login", "/ping", "/openapi.json", "/api/docs", "/logout"]

    if request.url.path.startswith("/static"):
        return await call_next(request)
        
    if request.url.path in rotas_publicas:
        return await call_next(request)

    # Checa o cookie
    session_token = request.cookies.get("maqcontrol_auth")
    if not session_token or session_token != "token_valido_admin":
        return RedirectResponse(url="/login",
        status_code=303)

    # Renova o cookie por mais 30 minutos (Inatividade)
    response = await call_next(request)
    response.set_cookie(key="maqcontrol_auth", value="token_valido_admin", httponly=True, max_age=1800)
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

from fastapi import Query

@app.post("/chamados/avancar-emergencial", include_in_schema=False)
async def avancar_chamado_emergencial(id: str = Query(...)):
    chamado = buscar_chamado(id)
    if not chamado:
        return {"status": "erro", "msg": "Chamado não encontrado"}
    
    status_atual = chamado.status.value if hasattr(chamado.status, 'value') else chamado.status
    novo_status = status_atual
    
    if status_atual == "Fila":
        novo_status = "Em Andamento"
    elif status_atual == "Em Andamento":
        novo_status = "Concluído"
    
    if novo_status != status_atual:
        payload = ChamadoUpdate(status=StatusChamado(novo_status))
        atualizar_chamado(id, payload)
        
    return {"status": "ok"}

@app.post("/chamados/voltar-emergencial", include_in_schema=False)
async def voltar_chamado_emergencial(id: str = Query(...)):
    chamado = buscar_chamado(id)
    if not chamado:
        return {"status": "erro", "msg": "Chamado não encontrado"}
    
    # Força a volta direta para a Fila conforme solicitado
    payload = ChamadoUpdate(status=StatusChamado.FILA)
    atualizar_chamado(id, payload)
        
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
