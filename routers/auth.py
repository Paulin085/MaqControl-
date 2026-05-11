# routers/auth.py — Rota de Autenticação Visual e Simulação
from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/login",
        name="login")
async def login_get(request: Request):
    """Renderiza a página de login visual."""
    return templates.TemplateResponse(request=request,
        name="login.html",
        context={"request": request},
    )

@router.post("/login")
async def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    """Simulação de login com usuário e senha fixos (admin/admin)."""
    if email == "admin" and password == "admin":
        # Simulando sucesso - Redirecionando para Dashboard (HTTP 302/303)
        response = RedirectResponse(url="/",
        status_code=303)
        response.set_cookie(key="maqcontrol_auth", value="token_valido_admin", httponly=True, max_age=1800)
        return response
    else:
        # Usuário/Senha inválidos
        return templates.TemplateResponse(request=request,
        name="login.html",
        context={
                "request": request, 
                "error": "Email ou senha inválidos. Tente admin / admin"
            },
        status_code=401
        )

@router.get("/logout",
        name="logout")
async def logout():
    """Limpa o cookie de sessão e redireciona para o login."""
    response = RedirectResponse(url="/login",
        status_code=303)
    response.delete_cookie("maqcontrol_auth")
    return response
