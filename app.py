"""Pohostinství AI – Slack event preview bot, READ/REPLY ONLY.
No Dotykačka, website or Facebook integration in this release.
"""
import hashlib
import hmac
import json
import logging
import os
import re
import threading
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pohostinstvi_ai")
_seen = {}
_lock = threading.Lock()


def verify_signature(body: bytes, headers: dict, secret: str, now=None) -> bool:
    if not secret:
        return False
    ts = headers.get("X-Slack-Request-Timestamp", "")
    signature = headers.get("X-Slack-Signature", "")
    if not ts.isdigit() or not signature.startswith("v0="):
        return False
    current = int(time.time() if now is None else now)
    if abs(current - int(ts)) > 300:
        return False
    base = b"v0:" + ts.encode("ascii") + b":" + body
    digest = "v0=" + hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


def parse_change(text: str):
    # Explicit syntax only: do not guess destructive actions from ambiguous messages.
    text = re.sub(r"\s+", " ", text.strip())
    pattern = (
        r"^do(?:š|s)el(?:a|o)?\s+(?P<old>[^,;]+)\s*[,;]\s*"
        r"nara(?:z|ž)il(?:i|a)?(?:\s+(?:jsem|jsme))?\s+(?P<new>.+?)"
        r"(?:\s*[,;]\s*cena\s*(?P<price>\d{1,4})(?:\s*k(?:č|c))?)?\s*\.?$"
    )
    match = re.match(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    old = match.group("old").strip(" .")
    new = match.group("new").strip(" .")
    if not old or not new or old.casefold() == new.casefold():
        return None
    price = match.group("price")
    if price is None:
        return {"old": old, "new": new, "price": None}
    value = int(price)
    if value <= 0 or value > 1000:
        return None
    return {"old": old, "new": new, "price": value}


def preview_text(change):
    if not change:
        return ("Příkaz jsem nerozpoznal. Použij například: "
                "`Došel Ogar Kazbek, narazil jsem Mazák 11°, cena 55 Kč.`\n"
                "*Zatím pouze test – žádné změny v Dotykačce.*")
    price = f"{change['price']} Kč" if change["price"] is not None else "neuvedena – doplň cenu"
    return ("*Pohostinství AI – náhled změny*\n"
            f"• Smazat produkt: *{change['old']}*\n"
            f"• Nové pivo na čepu: *{change['new']}*\n"
            f"• Cena: *{price}*\n"
            "• Kategorie: *Piva na čepu*\n\n"
            "*TESTOVACÍ REŽIM – NIC NEPROVEDENO.* "
            "V Dotykačce se nic nevytvořilo ani nesmazalo. "
            "Web a Facebook se nezměnily.")


def slack_reply(channel: str, thread_ts: str, text: str):
    token = os.getenv("SLACK_BOT_TOKEN", "")
    if not token:
        log.error("SLACK_BOT_TOKEN is missing")
        return
    payload = json.dumps({"channel": channel, "thread_ts": thread_ts, "text": text,
                          "unfurl_links": False, "unfurl_media": False}).encode("utf-8")
    req = Request("https://slack.com/api/chat.postMessage", data=payload,
                  headers={"Authorization": "Bearer " + token,
                           "Content-Type": "application/json; charset=utf-8"}, method="POST")
    try:
        with urlopen(req, timeout=8) as response:
            result = json.load(response)
        if not result.get("ok"):
            log.error("Slack reply failed: %s", result.get("error", "unknown"))
    except (URLError, HTTPError, TimeoutError) as exc:
        log.error("Slack reply request failed: %s", type(exc).__name__)


def is_new(event_id: str) -> bool:
    # In-memory de-duplication suffices only for this preview-only version.
    now = time.monotonic()
    with _lock:
        for key, created in list(_seen.items()):
            if now - created > 900:
                del _seen[key]
        if event_id in _seen:
            return False
        _seen[event_id] = now
        return True


def handle_event(body: bytes, headers: dict):
    """Return (HTTP status, JSON-compatible dict or None) for signed Slack event."""
    if len(body) > 65536:
        return 413, {"error": "Payload too large"}
    if not verify_signature(body, headers, os.getenv("SLACK_SIGNING_SECRET", "")):
        return 401, {"error": "Invalid Slack signature"}
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return 400, {"error": "Invalid JSON"}
    if not isinstance(data, dict):
        return 400, {"error": "Invalid event"}
    if data.get("type") == "url_verification":
        return 200, {"challenge": data.get("challenge", "")}
    if data.get("type") != "event_callback":
        return 200, {}
    event = data.get("event", {})
    if not isinstance(event, dict):
        return 200, {}
    if event.get("type") != "message" or event.get("subtype") or event.get("bot_id"):
        return 200, {}
    channel = event.get("channel", "")
    user = event.get("user", "")
    allowed_channel = os.getenv("SLACK_CHANNEL_ID", "")
    allowed_users = {x.strip() for x in os.getenv("SLACK_ALLOWED_USER_IDS", "").split(",") if x.strip()}
    if not allowed_channel or not allowed_users or channel != allowed_channel or user not in allowed_users:
        return 200, {}
    if event.get("thread_ts"):
        return 200, {}
    message = event.get("text", "")
    if not isinstance(message, str) or len(message) > 2000:
        return 200, {}
    if not re.match(r"^\s*do(?:š|s)el", message, re.IGNORECASE):
        return 200, {}
    event_id = data.get("event_id", "")
    if not event_id or not is_new(event_id):
        return 200, {}
    thread_ts = event.get("ts", "")
    if thread_ts:
        threading.Thread(target=slack_reply, args=(channel, thread_ts, preview_text(parse_change(message))), daemon=True).start()
    return 200, {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.respond(200, {"status": "ok", "mode": "preview-only", "version": "1.2"})
        else:
            self.respond(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/slack/events":
            return self.respond(404, {"error": "Not found"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.respond(400, {"error": "Invalid length"})
        if size < 0 or size > 65536:
            return self.respond(413, {"error": "Payload too large"})
        body = self.rfile.read(size)
        status, result = handle_event(body, self.headers)
        self.respond(status, result)

    def respond(self, status, result):
        payload = json.dumps(result, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        log.info("HTTP %s", fmt % args)


def run():
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    run()
