from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from crud.users import get_all_users, get_user_by_id, create_user, update_user, delete_user
from models.user import UserCreate, UserUpdate

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

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
        "users": users
    })

@router.post("/users/new")
async def admin_create_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    is_admin: bool = Form(False),
    perm_users: bool = Form(False),
    perm_maquinas: bool = Form(False),
    perm_setores: bool = Form(False),
    perm_chamados: bool = Form(False),
    perm_relatorios: bool = Form(False),
):
    user = get_admin_user(request)
    
    permissions = []
    if perm_users: permissions.append("users")
    if perm_maquinas: permissions.append("maquinas")
    if perm_setores: permissions.append("setores")
    if perm_chamados: permissions.append("chamados")
    if perm_relatorios: permissions.append("relatorios")
    
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
    perm_users: bool = Form(False),
    perm_maquinas: bool = Form(False),
    perm_setores: bool = Form(False),
    perm_chamados: bool = Form(False),
    perm_relatorios: bool = Form(False),
):
    user = get_admin_user(request)
    
    permissions = []
    if perm_users: permissions.append("users")
    if perm_maquinas: permissions.append("maquinas")
    if perm_setores: permissions.append("setores")
    if perm_chamados: permissions.append("chamados")
    if perm_relatorios: permissions.append("relatorios")
    
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
        # Prevent self-deletion if desired, or let it happen and user gets logged out
        raise HTTPException(status_code=400, detail="Não pode excluir a si mesmo.")
        
    delete_user(user_id)
    return RedirectResponse(url="/admin/users", status_code=303)
