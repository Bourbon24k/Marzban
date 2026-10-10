# Deployed template overrides

`templates/` contains the three active, non-secret templates read from the production data mount on 2026-10-10. `v2ray/default.json` and `subscription/index.html` differ from the image's `app/templates`; `v2ray/yuku_routing.json` matches it. Backups and `.DS_Store` were excluded.

The running panel sets `CUSTOM_TEMPLATES_DIRECTORY=/var/lib/marzban/templates/`. Jinja loads that directory before `app/templates`, so these overrides are necessary to reproduce deployed subscription JSON and the subscription page. They contain template variables, public routing/DNS lists and public UI assets, not subscriber credentials.

Copy the contents of `templates/` to the custom-template directory only as part of an explicitly authorized deployment, after backing up existing files. Publishing this directory does not apply it to a VPS. The actual Xray server configuration, private keys, certificates, environment secrets, database and real host-role map are deliberately not included.
