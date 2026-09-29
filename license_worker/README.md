# Online License Service

Free deployment target: Cloudflare Workers + D1 + Telegram Bot.

## 1. Create D1 database

```powershell
npx wrangler d1 create facebook-tool-license
```

Copy the returned database id into `wrangler.toml`, then apply the schema:

```powershell
npx wrangler d1 execute facebook-tool-license --remote --file=schema.sql
```

## 2. Configure secrets

Create a Telegram bot with BotFather and obtain the administrator chat id. Do not put the bot token in the client or commit it.

```powershell
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
```

Set `ADMIN_CHAT_ID` in `wrangler.toml` or as a Worker variable.

## 3. Deploy

```powershell
npx wrangler deploy
```

The Worker URL will be similar to:

```text
https://facebook-tool-license.<account>.workers.dev
```

## 4. Register the Telegram webhook

```powershell
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" `
	-d "url=https://facebook-tool-license.<account>.workers.dev/telegram/webhook" `
	-d "secret_token=<YOUR_WEBHOOK_SECRET>"
```

## 5. Configure the client

Replace `LICENSE_API_URL` in `client_app.py` with the Worker URL, then rebuild the EXE.

The client calls `POST /validate` with the 16-character key and HWID. The first successful validation binds the key to that HWID.

## Telegram commands

```text
/create 30
/activate ABCD-2345-EFGH-5678 HWID-...
/revoke ABCD-2345-EFGH-5678
/check ABCD-2345-EFGH-5678
```

Keys are stored as SHA-256 hashes in D1. The plaintext key is only returned once by `/create`.
