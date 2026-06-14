# YUKU VPN — патчи к Marzban v0.8.4

Форк [Gozargah/Marzban](https://github.com/Gozargah/Marzban) `v0.8.4` с патчами для:

1. **Обход блокировок через Yandex Cloud CDN** (XHTTP GET-uplink)
2. **Стабильность нод** (ноды перестали «падать» из-за таймаутов)
3. **Уведомление истёкшим подписчикам** в клиенте (как в Remnawave)

Все изменения — в 4 файлах (163 строки добавлено, 6 изменено). База ветки — тег `v0.8.4`,
проверено: оригиналы из развёрнутого образа `gozargah/marzban:latest` (2025-01-09) **байт-в-байт**
совпадают с тегом, дрейфа нет.

| Файл | ± строк | Назначение |
|------|---------|-----------|
| `app/subscription/v2ray.py` | +109 | XHTTP GET-uplink поля в генерации подписки |
| `app/subscription/share.py` | +41 | уведомление истёкшим юзерам |
| `app/xray/node.py` | ±13 | фикс таймаутов и `started` (стабильность нод) |
| `app/xray/config.py` | +6 | чтение XHTTP-полей из `xray_config.json` |

---

## Патч 1 — Yandex CDN XHTTP GET-uplink (`v2ray.py` + `config.py`)

### Проблема
Yandex Cloud CDN — кэширующий L7-прокси. Он режет `POST`-uplink (отвечает `405`), а mainline-XHTTP
шлёт uplink через POST → через Яндекс CDN интернета нет. Лазейка — `uplinkHTTPMethod: GET`
(PR [XTLS/Xray-core#5414](https://github.com/XTLS/Xray-core/pull/5414), влит в mainline 31.01.2026).
Чтобы это работало, поля XHTTP должны:
- читаться Marzban из `xray_config.json` при генерации настроек inbound (`app/xray/config.py`);
- попадать в подписку пользователя — и в VLESS-URL (`extra` dict), и в v2ray-json (`xhttpSettings`).

Stock Marzban v0.8.4 этих полей не знает и теряет их.

### Что добавлено

**`app/xray/config.py`** — в секции xhttp/splithttp читаются новые поля:
```python
settings["uplinkHTTPMethod"]   = net_settings.get("uplinkHTTPMethod", "")
settings["xPaddingKey"]        = net_settings.get("xPaddingKey", "")
settings["xPaddingMethod"]     = net_settings.get("xPaddingMethod", "")
settings["xPaddingObfsMode"]   = net_settings.get("xPaddingObfsMode", False)
settings["xPaddingPlacement"]  = net_settings.get("xPaddingPlacement", "")
settings["scStreamUpServerSecs"] = net_settings.get("scStreamUpServerSecs", "")
```

**`app/subscription/v2ray.py`** — три исправленных бага:
- `splithttp_config()` принимал новые параметры, но не писал их в `config` dict — добавлено.
- `make_stream_setting()` не передавал эти параметры в `splithttp_config()` — добавлено.
- `extra` dict в `vmess()` / `vless()` / `trojan()` содержал только `uplinkHTTPMethod`,
  без остальных полей — добавлены все. Сигнатуры методов расширены.

После патча подписка содержит полный набор XHTTP-полей и в base64-формате (VLESS-URL),
и в v2ray-json (для Happ/v2rayNG/Streisand).

> Требуется ядро Xray ≥ 26.x (после мерджа PR #5414) на сервере **и** клиенте.

---

## Патч 2 — стабильность нод (`app/xray/node.py`)

### Проблема
`XRayNode.started` (property) при таймауте бросал `NodeAPIError` вместо возврата `False`.
Это исключение прерывало `remove_user()` в середине цикла — истёкшие пользователи не вычищались
со всех нод. Плюс таймауты `/ping`, `/`, `/connect` были жёстко `3` секунды — при нагрузке/свопе
сервер не укладывался, ноды массово помечались как отключённые → шторм переподключений.

### Что изменено
```python
@property
def started(self):
    try:
        res = self.make_request("/", timeout=15)   # было timeout=3 БЕЗ try/except
        return res.get('started', False)
    except NodeAPIError:
        return False
```
Также таймауты `/ping` и `/connect` подняты `3 → 15` c, `/disconnect` `3 → 10` c.

После патча: `remove_user()` отрабатывает полностью; истёкшие корректно удаляются; ноды
перестали «падать» из-за коротких таймаутов.

---

## Патч 3 — уведомление истёкшим подписчикам (`app/subscription/share.py`)

### Идея (как в Remnawave)
Stock Marzban истёкшему юзеру отдаёт подписку с реальными (но уже нерабочими) серверами —
пользователь видит сервера, они не коннектятся, непонятно почему. Этот патч вместо мёртвых
серверов отдаёт **сервер-уведомление**: имя записи = текст уведомления, виден прямо в списке
серверов клиента.

### Что добавлено
- Константы перед `generate_subscription`:
  ```python
  DUMMY_NOTICE_UUID = "00000000-0000-0000-0000-000000000000"
  EXPIRED_NOTICE_LINES = [
      "🔴 Подписка закончилась",
      "➡️ Продлите: t.me/yuku_vpn_bot",   # ← здесь меняется текст/ссылка
  ]
  ```
- Helper `_generate_expired_notice(config_format)`:
  - `v2ray-json` (Happ) — собирает валидный JSON через `V2rayJsonConfig` с dummy-outbound на `127.0.0.1`;
  - `v2ray` и fallback — vless-ссылки с именем-уведомлением.
- Short-circuit в начале `generate_subscription`:
  ```python
  from app.models.user import UserStatus
  if getattr(user, "status", None) == UserStatus.expired:
      config = _generate_expired_notice(config_format)
      ...
      return config
  ```

### Настройка / ограничения
- **Текст уведомления** меняется в `EXPIRED_NOTICE_LINES` (в `app/subscription/share.py`).
- Покрыты форматы `v2ray` и `v2ray-json` (Happ, v2rayNG ≥1.8.29, Streisand). Для clash/sing-box/outline
  отдаётся fallback v2ray-ссылка.
- Срабатывает только для статуса `expired`. Для `limited` (кончился трафик) — при желании добавить
  статус в условие short-circuit.

---

## Сборка и деплой

```bash
# собрать образ из форка
docker build -t marzban-yuku .

# или использовать готовый образ (если опубликован в GHCR)
docker pull ghcr.io/bourbon24k/marzban:0.8.4-yuku
```

### Рекомендуемые env (`/opt/marzban/.env`)
- `XRAY_LOG_LEVEL=warning` — защита от переполнения диска X-Padding-строками XHTTP.

---

*Базовый проект — [Marzban](https://github.com/Gozargah/Marzban), лицензия AGPL-3.0.
Эти патчи распространяются на тех же условиях.*
