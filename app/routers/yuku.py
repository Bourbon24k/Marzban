from fastapi import APIRouter, Body, Depends

from app.db import Session, crud, get_db
from app.models.admin import Admin
from app.utils import responses

router = APIRouter(tags=["YUKU"], prefix="/api/yuku", responses={401: responses._401})

# Known settings with their defaults. Notice texts use \n to separate lines.
DEFAULT_SETTINGS = {
    "expired_notice": "🔴 Подписка закончилась\n➡️ Продлите: t.me/yuku_vpn_bot",
    "device_limit_notice": "🔴 Превышен лимит устройств\n➡️ Поддержка: t.me/yuku_vpn_bot",
    "default_device_limit": "0",
}


def get_merged_settings(db: Session) -> dict:
    """Stored settings merged over defaults."""
    merged = dict(DEFAULT_SETTINGS)
    stored = crud.get_yuku_settings(db)
    for k, v in stored.items():
        if v is not None:
            merged[k] = v
    return merged


@router.get("/settings")
def get_settings(
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """Get YUKU settings (notice texts, default device limit, etc.)."""
    return get_merged_settings(db)


@router.put("/settings")
def update_settings(
    values: dict = Body(...),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Update YUKU settings. Only known keys are accepted."""
    allowed = {k: v for k, v in values.items() if k in DEFAULT_SETTINGS}
    if allowed:
        crud.set_yuku_settings(db, allowed)
    return get_merged_settings(db)
