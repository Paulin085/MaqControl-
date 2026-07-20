from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from crud.users import get_all_users, get_user_by_id, create_user, update_user, delete_user
from models.user import UserCreate, UserUpdate

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

# Lista canônica de permissões disponíveis no sistema (fácil de estender no futuro)
AVAILABLE_PERMISSIONS = [
    ("abrir_chamado",   "Abrir Chamado",       "Permite abrir novos chamados"),
    ("meus_chamados",   "Meus Chamados",        "Ver lista dos próprios chamados"),
    ("chat",            "Chat",                 "Acessar o chat dos chamados"),
    ("gestao_setores",  "Gestão de Setores",    "Criar/editar/remover setores"),
    ("gestao_usuarios", "Gestão de Usuários",   "Gerenciar usuários e permissões"),
    ("maquinas",        "Máquinas",             "Acesso ao módulo de máquinas"),
    ("relatorios",      "Relatórios",           "Acesso a relatórios e exportações"),
]


def get_admin_user(request: Request):
    user = getattr(request.state, "user", None)
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores.")
    return user


@router.get("/")
async def admin_dashboard(request: Request):
    user = get_admin_user(request)
    users = get_all_users()

    return templates.TemplateResponse(request=request, name="admin/dashboard.html", context={
        "request": request,
        "user": user,
        "total_users": len(users)
    })


@router.get("/users")
async def admin_users_list(request: Request):
    user = get_admin_user(request)
    users = get_all_users()
    return templates.TemplateResponse(request=request, name="admin/users.html", context={
        "request": request,
        "user": user,
        "users": users,
        "available_permissions": AVAILABLE_PERMISSIONS,
    })


@router.post("/users/new")
async def admin_create_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    is_admin: bool = Form(False),
    # Permissões dinâmicas — lemos do form de forma flexível
):
    get_admin_user(request)

    form_data = await request.form()
    permissions = _extract_permissions(form_data)

    new_user = UserCreate(
        name=name,
        email=email,
        password=password,
        is_admin=is_admin,
        permissions=permissions
    )
    create_user(new_user)
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/edit")
async def admin_edit_user(
    request: Request,
    user_id: str,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(""),
    is_admin: bool = Form(False),
):
    get_admin_user(request)

    form_data = await request.form()
    permissions = _extract_permissions(form_data)

    update_data = UserUpdate(
        name=name,
        email=email,
        is_admin=is_admin,
        permissions=permissions,
        password=password if password else None
    )

    update_user(user_id, update_data)
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/delete")
async def admin_delete_user(request: Request, user_id: str):
    user = get_admin_user(request)
    if user.id == user_id:
        raise HTTPException(status_code=400, detail="Não pode excluir a si mesmo.")

    delete_user(user_id)
    return RedirectResponse(url="/admin/users", status_code=303)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_permissions(form_data) -> list:
    """Extrai todas as permissões marcadas no formulário."""
    permissions = []
    for perm_key, _, _ in AVAILABLE_PERMISSIONS:
        # Checkbox HTML envia o valor apenas quando marcado
        if form_data.get(f"perm_{perm_key}"):
            permissions.append(perm_key)
    return permissions
