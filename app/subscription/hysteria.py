"""Hysteria2 export formats. Panel/API protocol is Xray's `hysteria`."""
from copy import deepcopy
from urllib.parse import quote, urlencode


def share_link(remark, address, inbound, settings, server_description=None):
    from .v2ray import _server_fragment
    host = f"[{address}]" if ":" in address else address
    query = {"sni": inbound.get("sni") or address}
    if inbound.get("ais"):
        query["insecure"] = "1"
    if inbound.get("obfs_password"):
        query.update(obfs="salamander", **{"obfs-password": inbound["obfs_password"]})
    return (f"hysteria2://{quote(settings['auth'], safe='')}@{host}:{inbound['port']}/?"
            + urlencode(query) + "#" + _server_fragment(remark, server_description))


def xray_outbound(address, inbound, settings, tag="proxy"):
    transport = deepcopy(inbound.get("hysteria_settings", {}))
    transport.update(version=2, auth=settings["auth"])
    stream = {"network": "hysteria", "security": "tls", "hysteriaSettings": transport,
              "tlsSettings": {"serverName": inbound.get("sni") or address,
                              "allowInsecure": bool(inbound.get("ais")), "alpn": ["h3"]}}
    if inbound.get("finalmask"):
        stream["finalmask"] = deepcopy(inbound["finalmask"])
    return {"tag": tag, "protocol": "hysteria",
            "settings": {"version": 2, "address": address, "port": int(inbound["port"])},
            "streamSettings": stream}


def singbox_outbound(remark, address, inbound, settings):
    outbound = {"type": "hysteria2", "tag": remark, "server": address,
                "server_port": int(inbound["port"]), "password": settings["auth"],
                "tls": {"enabled": True, "server_name": inbound.get("sni") or address,
                        "insecure": bool(inbound.get("ais")), "alpn": ["h3"]}}
    if inbound.get("obfs_password"):
        outbound["obfs"] = {"type": "salamander", "password": inbound["obfs_password"]}
    return outbound


def mihomo_node(remark, address, inbound, settings):
    node = {"name": remark, "type": "hysteria2", "server": address,
            "port": int(inbound["port"]), "password": settings["auth"],
            "sni": inbound.get("sni") or address,
            "skip-cert-verify": bool(inbound.get("ais")), "alpn": ["h3"]}
    if inbound.get("obfs_password"):
        node.update(obfs="salamander", **{"obfs-password": inbound["obfs_password"]})
    return node
