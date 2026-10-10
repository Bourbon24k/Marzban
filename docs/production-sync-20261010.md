# Read-only production synchronization — 2026-10-10

The complete Marzban source was read from the running container, including bind-mounted subscription/database files and changes in its writable layer. A second live hash pass confirmed **444 source files** match this tree. Deployed dashboard assets were copied separately and matched by SHA-256. Generated bundle-analysis `stats.html`, Python caches, AppleDouble files, databases, certificate material, `.env`, subscriber configurations and host-role deployment data are excluded.

Compared with the previous GitHub main, production had 23 changed files and 11 additional files. The 33 source/lock files were synchronized; one additional file was the generated `stats.html` report. Previously existing node-recovery fixes and the Yuku client metadata integration are retained.

Included changes:

- Hysteria2 protocol models, Xray account protobuf, URI/Xray/sing-box/Mihomo exporters and dashboard controls; legacy Clash omits unsupported Hysteria2.
- Explicit inbound protocol validation, duplicate-credential conflict responses and Hysteria authentication redaction in audit logs.
- Master-only Hysteria inbounds/keys are filtered before distribution to remote nodes.
- Persisted host order with migration `yuku0013order`, plus Hysteria auth uniqueness migration `yuku0014hy2`.
- Client compatibility notices and description metadata, v2rayTun JSON dispatch; HWID enforcement remains in the main subscription route.
- Deployed Poland/Timeweb/Yandex XHTTP transport overrides and the current restricted pilot visibility rule.
- Current RU bypass/DNS routing templates and blocking fallback when automatic proxy selection fails.
- Numeric auto-select intervals with validation and correct persisted Xray duration, dashboard API-path fix and Hysteria form/types updates.

Checks: dashboard TypeScript/Vite production build passed. **24 tests** passed across node recovery, metadata, Yuku route/renderer, Hysteria model/export and migration checks. Migration graph has one head (`yuku0014hy2`); live database reports the same revision. Hysteria/model tests used a temporary local DB, an isolated package bootstrap and a fake version-only Xray executable; these do not prove actual tunnel performance. SQLite migration upgrade/index/downgrade behavior was tested on a temporary in-memory database. MySQL migration behavior and a full Docker image build were not tested.

Runtime Xray reports `26.3.27` with a dirty build; its binary and live configuration are not included as source in this synchronization. The existing Dockerfile fetches an installer for latest Xray, so a fresh image build is not guaranteed to reproduce that exact runtime binary. Published GHCR images are not updated by this commit.

No production files, configuration, containers or services were modified/restarted. Snapshot hashes are in `production-source-manifest-20261010.json`.

Reproduce isolated tests with installed requirements (plus `setuptools<81`):

```sh
python -m unittest discover -s tests -p test_node_recovery.py -v
python -m unittest discover -s tests -p test_native_metadata.py -v
python -m unittest discover -s tests -p test_yuku_client.py -v
python -m unittest discover -s tests -p test_production_migrations.py -v
python tests/run_isolated_hysteria.py
```
