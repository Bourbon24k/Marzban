from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.db import Session, crud, get_db
from app.dependencies import get_validated_user
from app.models.admin import Admin
from app.models.host_group import (
    HostGroupCreate,
    HostGroupModify,
    HostGroupResponse,
    UserGroupUsageResponse,
)
from app.utils import responses

router = APIRouter(
    tags=["HostGroup"], prefix="/api",
    responses={401: responses._401, 403: responses._403},
)


def _require_sudo(admin: Admin):
    if not admin.is_sudo:
        raise HTTPException(status_code=403, detail="You're not allowed")


def _group_response(g) -> HostGroupResponse:
    return HostGroupResponse(
        id=g.id,
        name=g.name,
        traffic_limit=g.traffic_limit,
        reset_strategy=g.reset_strategy,
        notice_text=g.notice_text,
        created_at=g.created_at,
        host_ids=[h.id for h in g.hosts],
        node_ids=[n.id for n in g.nodes],
    )


@router.get("/host-candidates")
def host_candidates(
    db: Session = Depends(get_db), admin: Admin = Depends(Admin.get_current)
):
    """Flat list of hosts (with ids) for the group editor's host picker."""
    from app.db.models import ProxyHost
    return [
        {"id": h.id, "remark": h.remark, "inbound_tag": h.inbound_tag,
         "address": h.address}
        for h in db.query(ProxyHost).order_by(ProxyHost.inbound_tag, ProxyHost.id).all()
    ]


@router.get("/host-groups", response_model=List[HostGroupResponse])
def list_host_groups(
    db: Session = Depends(get_db), admin: Admin = Depends(Admin.get_current)
):
    """List all host traffic groups."""
    return [_group_response(g) for g in crud.get_host_groups(db)]


@router.post("/host-group", response_model=HostGroupResponse,
             responses={409: responses._409})
def add_host_group(
    body: HostGroupCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    _require_sudo(admin)
    if crud.get_host_group_by_name(db, body.name):
        raise HTTPException(status_code=409, detail="Group already exists")
    return _group_response(crud.create_host_group(db, body))


@router.get("/host-group/{group_id}", response_model=HostGroupResponse,
            responses={404: responses._404})
def get_host_group(
    group_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    g = crud.get_host_group(db, group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    return _group_response(g)


@router.put("/host-group/{group_id}", response_model=HostGroupResponse,
            responses={404: responses._404})
def modify_host_group(
    group_id: int,
    body: HostGroupModify,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    _require_sudo(admin)
    g = crud.get_host_group(db, group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    return _group_response(crud.update_host_group(db, g, body))


@router.delete("/host-group/{group_id}", responses={404: responses._404})
def delete_host_group(
    group_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    _require_sudo(admin)
    g = crud.get_host_group(db, group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    crud.remove_host_group(db, g)
    return {"detail": "Group removed"}


# --- bot-facing / per-user endpoints -----------------------------------------

@router.get("/user/{username}/group-usage",
            response_model=List[UserGroupUsageResponse],
            responses={403: responses._403, 404: responses._404})
def get_user_group_usage(
    dbuser=Depends(get_validated_user),
    db: Session = Depends(get_db),
):
    """Per-group traffic usage of a user (for the bot's profile screen)."""
    groups = crud.get_host_groups(db)
    usages = {u.group_id: u for u in crud.get_user_group_usages(db, dbuser.id)}
    out = []
    for g in groups:
        u = usages.get(g.id)
        used = (u.used_traffic if u else 0) or 0
        limit = g.traffic_limit or 0
        out.append(UserGroupUsageResponse(
            group_id=g.id,
            group_name=g.name,
            used_traffic=used,
            traffic_limit=limit or None,
            remaining=max(limit - used, 0) if limit else None,
            over_limit=bool(limit) and used >= limit,
            reset_at=u.reset_at if u else None,
        ))
    return out


@router.post("/user/{username}/group/{group_id}/reset",
             responses={403: responses._403, 404: responses._404})
def reset_user_group(
    group_id: int,
    dbuser=Depends(get_validated_user),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """Reset a user's usage counter for one group (e.g. after they top up)."""
    _require_sudo(admin)
    if not crud.get_host_group(db, group_id):
        raise HTTPException(status_code=404, detail="Group not found")
    crud.reset_user_group_usage(db, dbuser.id, group_id)
    return {"detail": "Usage reset"}
