# Cloudflare migration runbook

Estado: migración preparada, no cortar Vercel/Supabase hasta validar Worker + D1.

## 1. Crear/aplicar D1

```powershell
wrangler d1 execute telegram-bot-news --file cloudflare/d1/schema.sql --remote
```

`wrangler.jsonc` ya apunta al binding `DB`.

## 2. Exportar datos desde Supabase

Requiere `.env` con `SUPABASE_URL` y `SUPABASE_KEY`.

```powershell
.venv\Scripts\python.exe -m cloudflare.d1.export_supabase_to_d1 > cloudflare/d1/import.sql
wrangler d1 execute telegram-bot-news --file cloudflare/d1/import.sql --remote
```

El SQL generado usa `INSERT OR REPLACE`, así que puede repetirse si necesitás reintentar.

## 3. Configurar Cloudflare secrets/vars

```powershell
wrangler secret put TELEGRAM_TOKEN
```

En `wrangler.jsonc`, reemplazar:

```jsonc
"ADMIN_CHAT_ID": "0"
```

por tu chat id real antes de probar comandos admin.

## 4. Validar antes de mover Telegram webhook

- `/api/stats` debe responder con stats desde D1.
- `/api/webhook` debe procesar `/start`, `/prices`, `/mercados`, `/noticias`, `/timezone`.
- El cron de Cloudflare debe actualizar `bot_health`.

Recién después de eso cambiar Telegram:

```text
https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<worker-domain>/api/webhook
```
