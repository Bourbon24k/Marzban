import base64
import random
import secrets
from collections import defaultdict
from datetime import datetime as dt
from datetime import timedelta
from typing import TYPE_CHECKING, List, Literal, Union

from jdatetime import date as jd

from app import xray
from app.utils.system import get_public_ip, get_public_ipv6, readable_size

from . import *

if TYPE_CHECKING:
    from app.models.user import UserResponse

from config import (
    ACTIVE_STATUS_TEXT,
    DISABLED_STATUS_TEXT,
    EXPIRED_STATUS_TEXT,
    LIMITED_STATUS_TEXT,
    ONHOLD_STATUS_TEXT,
)

SERVER_IP = get_public_ip()
SERVER_IPV6 = get_public_ipv6()

STATUS_EMOJIS = {
    "active": "✅",
    "expired": "⌛️",
    "limited": "🪫",
    "disabled": "❌",
    "on_hold": "🔌",
}

STATUS_TEXTS = {
    "active": ACTIVE_STATUS_TEXT,
    "expired": EXPIRED_STATUS_TEXT,
    "limited": LIMITED_STATUS_TEXT,
    "disabled": DISABLED_STATUS_TEXT,
    "on_hold": ONHOLD_STATUS_TEXT,
}


def generate_v2ray_links(proxies: dict, inbounds: dict, extra_data: dict, reverse: bool,
                         group_ctx: dict = None) -> list:
    format_variables = setup_format_variables(extra_data)
    conf = V2rayShareLink()
    return process_inbounds_and_tags(inbounds, proxies, format_variables, conf=conf,
                                     reverse=reverse, group_ctx=group_ctx)


def generate_clash_subscription(
        proxies: dict, inbounds: dict, extra_data: dict, reverse: bool, is_meta: bool = False,
        group_ctx: dict = None
) -> str:
    if is_meta is True:
        conf = ClashMetaConfiguration()
    else:
        conf = ClashConfiguration()

    format_variables = setup_format_variables(extra_data)
    return process_inbounds_and_tags(
        inbounds, proxies, format_variables, conf=conf, reverse=reverse, group_ctx=group_ctx
    )


def generate_singbox_subscription(
        proxies: dict, inbounds: dict, extra_data: dict, reverse: bool,
        group_ctx: dict = None
) -> str:
    conf = SingBoxConfiguration()

    format_variables = setup_format_variables(extra_data)
    return process_inbounds_and_tags(
        inbounds, proxies, format_variables, conf=conf, reverse=reverse, group_ctx=group_ctx
    )


def generate_outline_subscription(
        proxies: dict, inbounds: dict, extra_data: dict, reverse: bool,
        group_ctx: dict = None
) -> str:
    conf = OutlineConfiguration()

    format_variables = setup_format_variables(extra_data)
    return process_inbounds_and_tags(
        inbounds, proxies, format_variables, conf=conf, reverse=reverse, group_ctx=group_ctx
    )


def generate_v2ray_json_subscription(
        proxies: dict, inbounds: dict, extra_data: dict, reverse: bool,
        group_ctx: dict = None
) -> str:
    conf = V2rayJsonConfig()

    format_variables = setup_format_variables(extra_data)
    return process_inbounds_and_tags(
        inbounds, proxies, format_variables, conf=conf, reverse=reverse, group_ctx=group_ctx
    )


DUMMY_NOTICE_UUID = "00000000-0000-0000-0000-000000000000"
EXPIRED_NOTICE_LINES = [
    "🔴 Подписка закончилась",
    "➡️ Продлите: t.me/yuku_vpn_bot",
]
DEVICE_LIMIT_NOTICE_LINES = [
    "🔴 Превышен лимит устройств",
    "➡️ Поддержка: t.me/yuku_vpn_bot",
]


def _generate_notice(config_format: str, lines: list) -> str:
    """Возвращает подписку-уведомление (фейковые серверы с именами-сообщениями)."""
    from urllib.parse import quote

    if config_format == "v2ray-json":
        conf = V2rayJsonConfig()
        for remark in lines:
            outbound = {
                "tag": "proxy",
                "protocol": "vless",
                "settings": V2rayJsonConfig.vless_config(
                    address="127.0.0.1", port=443, id=DUMMY_NOTICE_UUID, flow=""
                ),
                "streamSettings": {"network": "tcp", "security": "none"},
            }
            conf.add_config(remarks=remark, outbounds=[outbound])
        return conf.render()

    links = [
        "vless://{}@127.0.0.1:443?security=none&type=tcp&headerType=none#{}".format(
            DUMMY_NOTICE_UUID, quote(line)
        )
        for line in lines
    ]
    return "\n".join(links)


import time as _time
_yuku_settings_cache = {"data": None, "ts": 0.0}


def _get_yuku_settings() -> dict:
    """Loads YUKU settings from DB with a 30s cache (notice texts etc.)."""
    now = _time.time()
    if _yuku_settings_cache["data"] is None or (now - _yuku_settings_cache["ts"]) > 30:
        try:
            from app.db import GetDB, crud
            with GetDB() as db:
                _yuku_settings_cache["data"] = crud.get_yuku_settings(db)
        except Exception:
            _yuku_settings_cache["data"] = {}
        _yuku_settings_cache["ts"] = now
    return _yuku_settings_cache["data"] or {}


# --- host traffic groups: cached host->group map + per-user enforcement ctx ----
_host_group_cache = {"map": None, "meta": None, "ts": 0.0}
DEFAULT_GROUP_NOTICE = "🔴 Лимит трафика группы исчерпан"


def _get_host_group_map():
    """Returns (host_id->group_id, group_id->meta). Cached 30s. Empty (=> the
    whole feature is inert) when there are no groups or the table is absent."""
    now = _time.time()
    if _host_group_cache["map"] is None or (now - _host_group_cache["ts"]) > 30:
        hmap, meta = {}, {}
        try:
            from app.db import GetDB
            from app.db.models import HostGroup
            with GetDB() as db:
                for g in db.query(HostGroup).all():
                    meta[g.id] = {
                        "name": g.name,
                        "traffic_limit": g.traffic_limit,
                        "notice_text": g.notice_text,
                    }
                    for h in g.hosts:
                        hmap[h.id] = g.id
        except Exception:
            hmap, meta = {}, {}
        _host_group_cache.update({"map": hmap, "meta": meta, "ts": now})
    return _host_group_cache["map"] or {}, _host_group_cache["meta"] or {}


def build_group_context(user) -> Union[dict, None]:
    """Per-user group state: host->group map + each group's used/limit/over.
    Returns None when there are no groups (callers then skip all group logic)."""
    host_group_map, group_meta = _get_host_group_map()
    if not host_group_map:
        return None
    uid = getattr(user, "id", None)
    if uid is None:
        return None
    try:
        from app.db import GetDB
        from app.db.models import UserGroupUsage
        with GetDB() as db:
            usage_rows = {
                r.group_id: (r.used_traffic or 0, r.traffic_limit, bool(r.member))
                for r in db.query(UserGroupUsage).filter(
                    UserGroupUsage.user_id == uid
                ).all()
            }
    except Exception:
        return None

    group_state = {}
    for gid, m in group_meta.items():
        used, override, member = usage_rows.get(gid, (0, None, False))
        # only users explicitly added to the group are limited/shown the cap
        if not member:
            continue
        # per-user override takes precedence over the group default
        limit = (override if override else m.get("traffic_limit")) or 0
        group_state[gid] = {
            "name": m.get("name"),
            "used": used,
            "limit": limit,
            "remaining": max(limit - used, 0) if limit else None,
            "over": bool(limit) and used >= limit,
            "notice_text": m.get("notice_text") or DEFAULT_GROUP_NOTICE,
        }
    if not group_state:
        return None  # user is in no group -> stay inert
    return {"host_group_map": host_group_map, "group_state": group_state}


def _notice_lines_from(key: str, default_lines: list) -> list:
    val = _get_yuku_settings().get(key)
    if val:
        lines = [ln for ln in val.split("\n") if ln.strip()]
        if lines:
            return lines
    return default_lines


def device_limit_notice_lines() -> list:
    """Notice lines shown when a user exceeds the device limit."""
    return _notice_lines_from("device_limit_notice", DEVICE_LIMIT_NOTICE_LINES)


DEFAULT_ANNOUNCE = "⚠️ Если не работает VPN, нажмите на 🔁 обновите подписку. Чтобы найти самый быстрый сервер используйте пинг"


def get_announce_text() -> str:
    """Subscription announce header text (editable via YUKU settings)."""
    val = _get_yuku_settings().get("announce")
    if val and val.strip():
        return val
    return DEFAULT_ANNOUNCE


def _generate_expired_notice(config_format: str) -> str:
    """Подписка-уведомление для истёкших (без реальных серверов)."""
    return _generate_notice(config_format, _notice_lines_from("expired_notice", EXPIRED_NOTICE_LINES))


def generate_subscription(
        user: "UserResponse",
        config_format: Literal["v2ray", "clash-meta", "clash", "sing-box", "outline", "v2ray-json"],
        as_base64: bool,
        reverse: bool,
        notice_lines: list = None,
) -> str:
    kwargs = {
        "proxies": user.proxies,
        "inbounds": user.inbounds,
        "extra_data": user.__dict__,
        "reverse": reverse,
        "group_ctx": build_group_context(user),
    }

    from app.models.user import UserStatus
    # Принудительное уведомление (например, превышен лимит устройств)
    if notice_lines:
        config = _generate_notice(config_format, notice_lines)
        if as_base64:
            config = base64.b64encode(config.encode()).decode()
        return config

    if getattr(user, "status", None) == UserStatus.expired:
        config = _generate_expired_notice(config_format)
        if as_base64:
            config = base64.b64encode(config.encode()).decode()
        return config

    if config_format == "v2ray":
        config = "\n".join(generate_v2ray_links(**kwargs))
    elif config_format == "clash-meta":
        config = generate_clash_subscription(**kwargs, is_meta=True)
    elif config_format == "clash":
        config = generate_clash_subscription(**kwargs)
    elif config_format == "sing-box":
        config = generate_singbox_subscription(**kwargs)
    elif config_format == "outline":
        config = generate_outline_subscription(**kwargs)
    elif config_format == "v2ray-json":
        config = generate_v2ray_json_subscription(**kwargs)
    else:
        raise ValueError(f'Unsupported format "{config_format}"')

    if as_base64:
        config = base64.b64encode(config.encode()).decode()

    return config


def format_time_left(seconds_left: int) -> str:
    if not seconds_left or seconds_left <= 0:
        return "∞"

    minutes, seconds = divmod(seconds_left, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    months, days = divmod(days, 30)

    result = []
    if months:
        result.append(f"{months}m")
    if days:
        result.append(f"{days}d")
    if hours and (days < 7):
        result.append(f"{hours}h")
    if minutes and not (months or days):
        result.append(f"{minutes}m")
    if seconds and not (months or days):
        result.append(f"{seconds}s")
    return " ".join(result)


def setup_format_variables(extra_data: dict) -> dict:
    from app.models.user import UserStatus

    user_status = extra_data.get("status")
    expire_timestamp = extra_data.get("expire")
    on_hold_expire_duration = extra_data.get("on_hold_expire_duration")
    now = dt.utcnow()
    now_ts = now.timestamp()

    if user_status != UserStatus.on_hold:
        if expire_timestamp is not None and expire_timestamp >= 0:
            seconds_left = expire_timestamp - int(dt.utcnow().timestamp())
            expire_datetime = dt.fromtimestamp(expire_timestamp)
            expire_date = expire_datetime.date()
            jalali_expire_date = jd.fromgregorian(
                year=expire_date.year, month=expire_date.month, day=expire_date.day
            ).strftime("%Y-%m-%d")
            if now_ts < expire_timestamp:
                days_left = (expire_datetime - dt.utcnow()).days + 1
                time_left = format_time_left(seconds_left)
            else:
                days_left = "0"
                time_left = "0"

        else:
            days_left = "∞"
            time_left = "∞"
            expire_date = "∞"
            jalali_expire_date = "∞"
    else:
        if on_hold_expire_duration is not None and on_hold_expire_duration >= 0:
            days_left = timedelta(seconds=on_hold_expire_duration).days
            time_left = format_time_left(on_hold_expire_duration)
            expire_date = "-"
            jalali_expire_date = "-"
        else:
            days_left = "∞"
            time_left = "∞"
            expire_date = "∞"
            jalali_expire_date = "∞"

    if extra_data.get("data_limit"):
        data_limit = readable_size(extra_data["data_limit"])
        data_left = extra_data["data_limit"] - extra_data["used_traffic"]
        if data_left < 0:
            data_left = 0
        data_left = readable_size(data_left)
    else:
        data_limit = "∞"
        data_left = "∞"

    status_emoji = STATUS_EMOJIS.get(extra_data.get("status")) or ""
    status_text = STATUS_TEXTS.get(extra_data.get("status")) or ""

    format_variables = defaultdict(
        lambda: "<missing>",
        {
            "SERVER_IP": SERVER_IP,
            "SERVER_IPV6": SERVER_IPV6,
            "USERNAME": extra_data.get("username", "{USERNAME}"),
            "DATA_USAGE": readable_size(extra_data.get("used_traffic")),
            "DATA_LIMIT": data_limit,
            "DATA_LEFT": data_left,
            "DAYS_LEFT": days_left,
            "EXPIRE_DATE": expire_date,
            "JALALI_EXPIRE_DATE": jalali_expire_date,
            "TIME_LEFT": time_left,
            "STATUS_EMOJI": status_emoji,
            "STATUS_TEXT": status_text,
        },
    )

    return format_variables


def process_inbounds_and_tags(
        inbounds: dict,
        proxies: dict,
        format_variables: dict,
        conf: Union[
            V2rayShareLink,
            V2rayJsonConfig,
            SingBoxConfiguration,
            ClashConfiguration,
            ClashMetaConfiguration,
            OutlineConfiguration
        ],
        reverse=False,
        group_ctx: dict = None,
) -> Union[List, str]:
    _inbounds = []
    for protocol, tags in inbounds.items():
        for tag in tags:
            _inbounds.append((protocol, [tag]))
    index_dict = {proxy: index for index, proxy in enumerate(
        xray.config.inbounds_by_tag.keys())}
    inbounds = sorted(
        _inbounds, key=lambda x: index_dict.get(x[1][0], float('inf')))

    _noticed_groups: set = set()  # groups whose over-limit notice was already added

    for protocol, tags in inbounds:
        settings = proxies.get(protocol)
        if not settings:
            continue

        format_variables.update({"PROTOCOL": protocol.name})
        for tag in tags:
            inbound = xray.config.inbounds_by_tag.get(tag)
            if not inbound:
                continue

            format_variables.update({"TRANSPORT": inbound["network"]})
            host_inbound = inbound.copy()
            for host in xray.hosts.get(tag, []):
                # host traffic group: inject per-group remark vars + enforce limit
                group_over = False
                group_notice = None
                group_label = ""  # auto-appended usage shown to the user
                if group_ctx:
                    gid = group_ctx["host_group_map"].get(host.get("id"))
                    gs = group_ctx["group_state"].get(gid) if gid is not None else None
                    if gs:
                        _gb = 1024 ** 3
                        _fmt_gb = lambda b: "{:.1f} ГБ".format((b or 0) / _gb)
                        format_variables.update({
                            "GROUP_USED": _fmt_gb(gs["used"]),
                            "GROUP_LIMIT": _fmt_gb(gs["limit"]) if gs["limit"] else "∞",
                            "GROUP_REMAINING": _fmt_gb(gs["remaining"])
                            if gs["remaining"] is not None else "∞",
                        })
                        group_over = gs["over"]
                        group_notice = gs["notice_text"]
                        # auto-show the cap to the user (members with a limit only),
                        # in GB; skipped if the remark already uses a {GROUP_*} var
                        if gs["limit"] and "{GROUP_" not in host["remark"]:
                            group_label = " ({:.1f}/{:.1f} ГБ)".format(
                                gs["used"] / _gb, gs["limit"] / _gb
                            )

                sni = ""
                sni_list = host["sni"] or inbound["sni"]
                if sni_list:
                    salt = secrets.token_hex(8)
                    sni = random.choice(sni_list).replace("*", salt)

                if sids := inbound.get("sids"):
                    inbound["sid"] = random.choice(sids)

                req_host = ""
                req_host_list = host["host"] or inbound["host"]
                if req_host_list:
                    salt = secrets.token_hex(8)
                    req_host = random.choice(req_host_list).replace("*", salt)

                address = ""
                address_list = host['address']
                if host['address']:
                    salt = secrets.token_hex(8)
                    address = random.choice(address_list).replace('*', salt)

                if host["path"] is not None:
                    path = host["path"].format_map(format_variables)
                else:
                    path = inbound.get("path", "").format_map(format_variables)

                if host.get("use_sni_as_host", False) and sni:
                    req_host = sni

                host_inbound.update(
                    {
                        "port": host["port"] or inbound["port"],
                        "sni": sni,
                        "host": req_host,
                        "tls": inbound["tls"] if host["tls"] is None else host["tls"],
                        "alpn": host["alpn"] if host["alpn"] else None,
                        "path": path,
                        "fp": host["fingerprint"] or inbound.get("fp", ""),
                        "ais": host["allowinsecure"]
                        or inbound.get("allowinsecure", ""),
                        "mux_enable": host["mux_enable"],
                        "fragment_setting": host["fragment_setting"],
                        "noise_setting": host["noise_setting"],
                        "random_user_agent": host["random_user_agent"],
                    }
                )

                if group_over:
                    gid_over = group_ctx["host_group_map"].get(host.get("id"))
                    if gid_over in _noticed_groups:
                        # already added the notice for this group — skip all other hosts
                        continue
                    _noticed_groups.add(gid_over)
                    # multi-line notice -> one fake server per line (the client shows
                    # only the first line of a single entry's name otherwise)
                    notice_lines = [ln for ln in group_notice.split("\n") if ln.strip()] \
                        or [group_notice]
                    for line in notice_lines:
                        conf.add(
                            remark=line.format_map(format_variables),
                            address="127.0.0.1",
                            inbound=host_inbound,
                            settings=settings.model_dump()
                        )
                else:
                    conf.add(
                        remark=host["remark"].format_map(format_variables) + group_label,
                        address=address.format_map(format_variables),
                        inbound=host_inbound,
                        settings=settings.model_dump()
                    )

    return conf.render(reverse=reverse)


def encode_title(text: str) -> str:
    return f"base64:{base64.b64encode(text.encode()).decode()}"
