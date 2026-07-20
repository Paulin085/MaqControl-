# routers/auth.py — Rota de Autenticação Visual e Real
from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from crud.users import get_user_by_email, verify_password

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", name="login")
async def login_get(request: Request):
    """Renderiza a página de login visual."""
    return templates.TemplateResponse(request=request,
        name="login.html",
        context={"request": request},
    )


@router.post("/login")
async def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    """Validação de login com usuário real armazenado em users.json."""
    user = get_user_by_email(email)

    if user and verify_password(password, user.hashed_password):
        # Redireciona para o portal correto: TI → Dashboard, Colaborador → Portal
        destino = "/" if user.is_admin else "/colaborador/"
        response = RedirectResponse(url=destino, status_code=303)
        response.set_cookie(key="maqcontrol_auth", value=user.id, httponly=True, max_age=86400)
        return response
    else:
        return templates.TemplateResponse(request=request,
            name="login.html",
            context={
                "request": request,
                "error": "Email ou senha inválidos."
            },
            status_code=401
        )


@router.get("/logout", name="logout")
async def logout():
    """Limpa o cookie de sessão e redireciona para o login."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("maqcontrol_auth")
    return response
