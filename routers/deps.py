from fastapi import Request
from crud.users import get_user_by_id
from models.user import User

def get_current_user(request: Request) -> User | None:
    user_id = request.cookies.get("maqcontrol_auth")
    if not user_id:
        return None
    return get_user_by_id(user_id)
