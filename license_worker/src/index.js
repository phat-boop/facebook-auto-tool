const KEY_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function normalizeKey(value) {
  return String(value || "").trim().toUpperCase();
}

function isLicenseKey(value) {
  return /^[A-Z2-7]{4}(?:-[A-Z2-7]{4}){3}$/.test(value);
}

async function sha256(value) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function randomKey() {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  const raw = [...bytes].map((byte) => KEY_ALPHABET[byte % KEY_ALPHABET.length]).join("");
  return `${raw.slice(0, 4)}-${raw.slice(4, 8)}-${raw.slice(8, 12)}-${raw.slice(12, 16)}`;
}

function parseDuration(text) {
  const days = Number.parseInt(text, 10);
  return Number.isInteger(days) && days > 0 && days <= 36500 ? days : null;
}

async function validateLicense(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ valid: false, message: "JSON không hợp lệ." }, 400);
  }

  const key = normalizeKey(body.key);
  const hwid = String(body.hwid || "").trim().toUpperCase();
  if (!isLicenseKey(key) || !hwid || hwid.length > 128) {
    return json({ valid: false, message: "Key hoặc HWID không hợp lệ." }, 400);
  }

  const row = await env.DB.prepare(
    "SELECT expires_at, status, hwid FROM licenses WHERE key_hash = ?1",
  ).bind(await sha256(key)).first();
  if (!row || row.status !== "active") {
    return json({ valid: false, message: "Key không tồn tại hoặc đã bị khóa." });
  }
  if (row.hwid && row.hwid !== hwid) {
    return json({ valid: false, message: "Key đã được kích hoạt trên máy khác." });
  }
  if (Date.parse(row.expires_at) <= Date.now()) {
    return json({ valid: false, message: "Key đã hết hạn." });
  }

  if (!row.hwid) {
    await env.DB.prepare(
      "UPDATE licenses SET hwid = ?1, activated_at = ?2 WHERE key_hash = ?3",
    ).bind(hwid, new Date().toISOString(), await sha256(key)).run();
  }
  return json({ valid: true, expires: row.expires_at.slice(0, 10) });
}

async function telegramSend(env, chatId, text) {
  const response = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text }),
  });
  if (!response.ok) {
    const details = await response.text();
    console.error("Telegram sendMessage failed", {
      status: response.status,
      details,
    });
    throw new Error(`Telegram API error (${response.status})`);
  }
}

async function handleTelegram(request, env) {
  const webhookSecret = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
  if (!env.TELEGRAM_WEBHOOK_SECRET || webhookSecret !== env.TELEGRAM_WEBHOOK_SECRET) {
    console.warn("Telegram webhook rejected: secret mismatch", {
      hasHeader: Boolean(webhookSecret),
      hasConfiguredSecret: Boolean(env.TELEGRAM_WEBHOOK_SECRET),
    });
    return json({ error: "Unauthorized" }, 401);
  }
  try {
    const update = await request.json();
    const message = update.message;
    console.log("Telegram update received", {
      chatId: message?.chat?.id || null,
      command: message?.text?.split(/\s+/)[0] || null,
      expectedChatIdConfigured: Boolean(env.ADMIN_CHAT_ID),
    });
    if (!message?.text || String(message.chat.id) !== String(env.ADMIN_CHAT_ID)) {
      console.warn("Telegram message ignored: chat ID mismatch or empty text");
      return json({ ok: true });
    }

    const [command, ...args] = message.text.trim().split(/\s+/);
    const chatId = message.chat.id;
    if (command === "/create") {
    const days = parseDuration(args[0]);
    if (!days) return telegramSend(env, chatId, "Dùng: /create <số_ngày>, ví dụ /create 30").then(() => json({ ok: true }));
    let key;
    let hash;
    do {
      key = randomKey();
      hash = await sha256(key);
    } while (await env.DB.prepare("SELECT key_hash FROM licenses WHERE key_hash = ?1").bind(hash).first());
    const expires = new Date(Date.now() + days * 86400000).toISOString();
    await env.DB.prepare(
      "INSERT INTO licenses (key_hash, key_hint, expires_at, status, created_at) VALUES (?1, ?2, ?3, 'active', ?4)",
    ).bind(hash, key.slice(-4), expires, new Date().toISOString()).run();
    await telegramSend(env, chatId, `Key mới (${days} ngày):\n${key}\nHạn: ${expires.slice(0, 10)}`);
    } else if (command === "/activate") {
    const key = normalizeKey(args[0]);
    const hwid = String(args[1] || "").trim().toUpperCase();
    if (!isLicenseKey(key) || !hwid) await telegramSend(env, chatId, "Dùng: /activate KEY HWID");
    else {
      const result = await env.DB.prepare("UPDATE licenses SET hwid = ?, activated_at = ? WHERE key_hash = ? AND status = 'active'").bind(hwid, new Date().toISOString(), await sha256(key)).run();
      await telegramSend(env, chatId, result.meta.changes ? "Đã gắn HWID." : "Không tìm thấy key active.");
    }
    } else if (command === "/revoke") {
    const key = normalizeKey(args[0]);
    const result = await env.DB.prepare("UPDATE licenses SET status = 'revoked' WHERE key_hash = ?").bind(await sha256(key)).run();
    await telegramSend(env, chatId, result.meta.changes ? "Đã khóa key." : "Không tìm thấy key.");
    } else if (command === "/check") {
    const key = normalizeKey(args[0]);
    const row = await env.DB.prepare("SELECT key_hint, hwid, expires_at, status FROM licenses WHERE key_hash = ?").bind(await sha256(key)).first();
    await telegramSend(env, chatId, row ? `Key ...${row.key_hint}\nHWID: ${row.hwid || 'chưa kích hoạt'}\nHạn: ${row.expires_at.slice(0, 10)}\nTrạng thái: ${row.status}` : "Không tìm thấy key.");
    } else {
      await telegramSend(env, chatId, "/create <ngày>\n/activate <key> <hwid>\n/revoke <key>\n/check <key>");
    }
    return json({ ok: true });
  } catch (error) {
    console.error("Telegram webhook error", error);
    return json({ ok: false, error: "Telegram handler failed" }, 500);
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/validate") return validateLicense(request, env);
    if (request.method === "POST" && url.pathname === "/telegram/webhook") return handleTelegram(request, env);
    if (request.method === "GET" && url.pathname === "/telegram/status") {
      return json({
        ok: true,
        telegramBotTokenConfigured: Boolean(env.TELEGRAM_BOT_TOKEN),
        telegramWebhookSecretConfigured: Boolean(env.TELEGRAM_WEBHOOK_SECRET),
        adminChatIdConfigured: Boolean(env.ADMIN_CHAT_ID),
      });
    }
    if (request.method === "GET" && url.pathname === "/health") return json({ ok: true });
    return json({ error: "Not found" }, 404);
  },
};
