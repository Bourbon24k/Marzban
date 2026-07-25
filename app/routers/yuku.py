from fastapi import APIRouter, Body, Depends

from app.db import Session, crud, get_db
from app.models.admin import Admin
from app.subscription.share import (
    ANNOUNCE_VARIABLES,
    DEFAULT_ANNOUNCE,
    invalidate_yuku_settings_cache,
)
from app.utils import audit, responses

router = APIRouter(tags=["YUKU"], prefix="/api/yuku", responses={401: responses._401})

# Known settings with their defaults. Notice texts use \n to separate lines.
DEFAULT_SETTINGS = {
    "expired_notice": "🔴 Подписка закончилась\n➡️ Продлите: t.me/yuku_vpn_bot",
    "device_limit_notice": "🔴 Превышен лимит устройств\n➡️ Поддержка: t.me/yuku_vpn_bot",
    "default_device_limit": "0",
    "announce": DEFAULT_ANNOUNCE,
    # "left" (as authored) or "center" (lines space-padded before sending)
    "announce_align": "left",
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
        current = get_merged_settings(db)
        audit.detail(
            target_name=",".join(sorted(allowed)),
            before={k: current.get(k) for k in allowed},
            after=dict(allowed),
        )
        crud.set_yuku_settings(db, allowed)
        # subscription reads settings through a 30s cache; drop it so the new
        # announce/notice text applies to the very next /sub request
        invalidate_yuku_settings_cache()
    return get_merged_settings(db)


@router.get("/announce-variables")
def announce_variables(admin: Admin = Depends(Admin.get_current)):
    """Template variables available in the announce text."""
    return {"variables": list(ANNOUNCE_VARIABLES)}
