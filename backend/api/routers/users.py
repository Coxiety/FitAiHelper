import secrets

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import get_current_user
from core.database import get_db
from models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get the currently logged in user."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "role": current_user.role.value,   # chỉ đọc; quyền thật luôn do server kiểm (require_admin)
        "telegram_linked": current_user.telegram_chat_id is not None,
    }


@router.post("/me/telegram-link")
async def create_telegram_link_code(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tạo (hoặc cấp lại) mã liên kết Telegram 8 ký tự cho tài khoản hiện tại."""
    code = secrets.token_hex(4).upper()
    current_user.telegram_link_code = code
    await db.commit()
    return {
        "telegram_linked": current_user.telegram_chat_id is not None,
        "link_code": code,
    }


@router.delete("/me/telegram-link")
async def unlink_telegram(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Huỷ liên kết Telegram khỏi tài khoản hiện tại."""
    current_user.telegram_chat_id = None
    current_user.telegram_link_code = None
    await db.commit()
    return {"telegram_linked": False}
