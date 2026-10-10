# Yuku iOS client integration

The main subscription route recognizes `Yuku/` as Xray JSON and adds `meta.yuku` only for this user agent. Existing HWID/device limits and expired, disabled and traffic-limit responses remain in the main route. Other clients retain their existing formats and order.

Physical profiles include `schemaVersion`, `hostID`, `networkRole` and `autoSelectGroup`. Generated balancer profiles are marked `kind: automatic`. Roles are operator-defined, never guessed from a display name. Missing/invalid mapping yields `unknown` and safely disables Ultra selection.

Set `YUKU_CLIENT_METADATA_PATH` to a small JSON file readable by the panel; default `/var/lib/marzban/yuku-native-hosts.json`. Start with `yuku-native-hosts.example.json` and replace placeholder host IDs and roles. The mapping is reread per subscription; do not publish real subscriber configurations or credentials.

The initial client integration was ported separately. A subsequent read-only audit synchronized all deployed Marzban source changes; see production-sync-20261010.md. Deployment and real iPhone VPN traffic are separate checks.
