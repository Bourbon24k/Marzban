"""Explicit operator metadata for the first-party iOS client; no name guesses."""
import json
import math
import os


def metadata_for_host(host):
    host_id = host.get("id")
    if isinstance(host_id, bool) or not isinstance(host_id, (int, str)):
        return None
    entry = {}
    path = os.environ.get("YUKU_CLIENT_METADATA_PATH", "/var/lib/marzban/yuku-native-hosts.json")
    if path:
        try:
            # Small deployment config, read anew so an operator edit takes effect.
            with open(path, encoding="utf-8") as stream:
                text = stream.read(1024 * 1024 + 1)
            if len(text) <= 1024 * 1024:
                mapping = json.loads(text)
                if isinstance(mapping, dict) and isinstance(mapping.get(str(host_id)), dict):
                    entry = mapping[str(host_id)]
        except (OSError, ValueError, TypeError):
            pass
    role = entry.get("networkRole")
    if role not in ("normal", "lte"):
        role = "unknown"
    group = host.get("auto_select") or 0
    if isinstance(group, bool):
        group = int(group)
    if not isinstance(group, int) or group < 0:
        group = 0
    result = {"schemaVersion": 1, "kind": "server", "hostID": str(host_id), "networkRole": role, "autoSelectGroup": group}
    country = entry.get("countryCode")
    if isinstance(country, str) and len(country) == 2 and country.isascii() and country.isalpha():
        result["countryCode"] = country.upper()
    lat, lon = entry.get("latitude"), entry.get("longitude")
    if (not isinstance(lat, bool) and not isinstance(lon, bool)
            and isinstance(lat, (int, float)) and isinstance(lon, (int, float))
            and math.isfinite(lat) and math.isfinite(lon)
            and -90 <= lat <= 90 and -180 <= lon <= 180):
        result.update(latitude=lat, longitude=lon)
    return result
