import json
import os
import hashlib
from typing import List, Optional
from models.user import User, UserCreate, UserUpdate

DATA_FILE = "data/users.json"

def get_password_hash(password: str) -> str:
    """Retorna um hash SHA256 simples da senha."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_password_hash(plain_password) == hashed_password

def _load_data() -> List[dict]:
    if not os.path.exists(DATA_FILE):
        _initialize_data()
        
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def _save_data(data: List[dict]):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def _initialize_data():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    
    # Criar admin padrão se não houver usuários
    default_admin = {
        "id": "admin-1",
        "name": "Administrador",
        "email": "admin",
        "hashed_password": get_password_hash("admin"),
        "is_admin": True,
        "permissions": ["users", "maquinas", "setores", "relatorios", "chamados"]
    }
    _save_data([default_admin])

def get_all_users() -> List[User]:
    data = _load_data()
    return [User(**item) for item in data]

def get_user_by_id(user_id: str) -> Optional[User]:
    users = get_all_users()
    for u in users:
        if u.id == user_id:
            return u
    return None

def get_user_by_email(email: str) -> Optional[User]:
    users = get_all_users()
    for u in users:
        if u.email == email:
            return u
    return None

def create_user(user_in: UserCreate) -> User:
    users_data = _load_data()
    
    new_user = User(
        name=user_in.name,
        email=user_in.email,
        is_admin=user_in.is_admin,
        permissions=user_in.permissions,
        hashed_password=get_password_hash(user_in.password)
    )
    
    users_data.append(new_user.model_dump())
    _save_data(users_data)
    return new_user

def update_user(user_id: str, user_in: UserUpdate) -> Optional[User]:
    users_data = _load_data()
    updated_user = None
    
    for i, u in enumerate(users_data):
        if u["id"] == user_id:
            if user_in.name is not None:
                users_data[i]["name"] = user_in.name
            if user_in.email is not None:
                users_data[i]["email"] = user_in.email
            if user_in.is_admin is not None:
                users_data[i]["is_admin"] = user_in.is_admin
            if user_in.permissions is not None:
                users_data[i]["permissions"] = user_in.permissions
            if user_in.password is not None and user_in.password.strip():
                users_data[i]["hashed_password"] = get_password_hash(user_in.password)
                
            updated_user = User(**users_data[i])
            break
            
    if updated_user:
        _save_data(users_data)
    return updated_user

def delete_user(user_id: str) -> bool:
    users_data = _load_data()
    filtered = [u for u in users_data if u["id"] != user_id]
    
    if len(filtered) < len(users_data):
        _save_data(filtered)
        return True
    return False
