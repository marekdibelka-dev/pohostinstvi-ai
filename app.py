"""Pohostinství AI – Slack beer changes and opt-in Facebook publishing.
Dotykačka and website remain disconnected.
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
from datetime import datetime, timezone
import facebook

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
    """Conservative Czech natural-language patterns; never invent missing names.

    This is NOT an LLM. Ambiguous phrasing must be clarified before any future write.
    """
    text = re.sub(r"\s+", " ", text.strip()).strip(" .!?")
    if not text or len(text) > 500:
        return None

    # Price must be explicit. Remove it before recognizing product names.
    price_matches = list(re.finditer(
        r"(?:[,;]\s*)?(?:cena(?:\s+je)?\s*[:=]?\s*|za\s+)(\d{1,4})\s*(?:kč|kc|,-)?(?=$|[,;.!?]\s*$)",
        text, flags=re.IGNORECASE))
    price = None
    if not price_matches:
        price_matches = list(re.finditer(r"[,;]\s*(\d{1,4})\s*(?:kč|kc|,-)?(?=$|[,;.!?]\s*$)", text, flags=re.IGNORECASE))
    if price_matches:
        match = price_matches[-1]
        price = int(match.group(1))
        if not 1 <= price <= 1000:
            return None
        text = (text[:match.start()] + text[match.end():]).strip(" ,;.!?")

    # Phrases that unambiguously identify both the old and new beer.
    patterns = [
        r"^do(?:š|s)el(?:a|o)?\s+(?P<old>.+?)\s*[,;]\s*nara(?:z|ž)il(?:i|a)?(?:\s+(?:jsem|jsme))?\s+(?P<new>.+)$",
        r"^do(?:š|s)el(?:a|o)?\s+(?P<old>.+?)\s*[,;]\s*(?:dej|dáme|dame|máme|mame|teď|ted)\s+(?:tam\s+|místo\s+něj\s+|misto\s+nej\s+)?(?P<new>.+)$",
        r"^(?:vyměň|vymen|vyměňte|vymenit|nahraď|nahrad|nahradit)\s+(?P<old>.+?)\s+za\s+(?P<new>.+)$",
        r"^nara(?:z|ž)il(?:i|a)?(?:\s+(?:jsem|jsme))?\s+(?P<new>.+?)\s+místo\s+(?P<old>.+)$",
        r"^(?P<old>.+?)\s+je\s+(?:prázdn(?:ý|y|á|a)|pryč|vypit(?:ý|y))\s*[,;]\s*místo\s+(?:něj|toho)\s+(?:máme|mame|je|dáme|dame)\s+(?P<new>.+)$",
    ]
    for pattern in patterns:
        m = re.match(pattern, text, flags=re.IGNORECASE)
        if not m:
            continue
        old = m.group("old").strip(" ,;.!?")
        new = m.group("new").strip(" ,;.!?")
        if not old or not new or old.casefold() == new.casefold():
            return None
        # Avoid treating vague prose as a product name.
        if len(old) > 90 or len(new) > 90 or any(x in old.casefold() for x in ("nějak", "něco", "jiné pivo")):
            return None
        return {"old": old, "new": new, "price": price}
    return None


def is_change_intent(message: str) -> bool:
    """Avoid replying to unrelated channel chatter."""
    return bool(re.search(r"\b(došel|dosel|došla|dosla|vyměň|vymen|nahraď|nahrad|narazil|narazili|prázdný|prazdny)\b", message, re.IGNORECASE))


def preview_text(change):
    if not change:
        return ("Výměnu nedokážu jednoznačně určit. Napiš prosím staré pivo, nové pivo a cenu, například: "
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


def process_change(channel, thread_ts, event_id, message, received_at):
    change = parse_change(message)
    if not change:
        return slack_reply(channel, thread_ts, preview_text(None))
    if change['price'] is None:
        return slack_reply(channel, thread_ts,
            f"Rozpoznal jsem nové pivo *{change['new']}*, ale chybí cena. "
            "Doplň ji prosím v nové zprávě s celou výměnou. Nic se nezveřejnilo.")
    if not facebook.allowed_at(received_at):
        return slack_reply(channel, thread_ts,
            "Výměna rozpoznána, ale mimo publikační čas (pá/so 18–21, ne 16–20). "
            "Příspěvek se nevytvořil ani neodkládá na později.")
    if not facebook.publishing_configured():
        return slack_reply(channel, thread_ts,
            "*Facebook – testovací náhled*\n" + facebook.caption(change) +
            "\n\nAutomatické zveřejnění není zatím aktivní; chybí Meta přístup nebo nastavení.")
    db = os.environ['FB_DB_PATH']
    try:
        if not facebook.claim_event(event_id, db):
            return  # Duplicate Slack event: never publish twice.
        try:
            # Strict wall-clock cutoff: do not publish after the configured window.
            if not facebook.allowed_at(datetime.now(timezone.utc)):
                facebook.complete_event(event_id, db, 'outside_window')
                return slack_reply(channel, thread_ts,
                    'Publikační čas mezitím skončil. Facebook příspěvek se nezveřejnil.')
            post_id = facebook.post_photo(change, os.environ['FB_PAGE_ACCESS_TOKEN'],
                                           os.environ['FB_PAGE_ID'],
                                           os.getenv('FB_GRAPH_VERSION', 'v26.0'))
            facebook.complete_event(event_id, db, 'published', post_id)
            slack_reply(channel, thread_ts, f"Facebook: zveřejněno nové pivo *{change['new']}* "
                        f"za {change['price']} Kč. ID: `{post_id}`")
        except Exception:
            # A network timeout can occur AFTER Facebook publishes; never retry automatically.
            log.exception('Facebook publication failed or outcome uncertain')
            facebook.complete_event(event_id, db, 'uncertain')
            slack_reply(channel, thread_ts,
                        "Zveřejnění na Facebooku se nepodařilo potvrdit. "
                        "Zkontroluj stránku; kvůli riziku duplicity systém automaticky neopakuje požadavek.")
    except Exception:
        log.exception('Persistent publication deduplication failed')
        slack_reply(channel, thread_ts, 'Facebook nezveřejněn: chyba evidence událostí.')


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
    # All human members who can post in this Slack channel may submit a preview.
    # Slack HMAC authenticates the event; channel access is administered in Slack.
    if not allowed_channel or channel != allowed_channel or not user:
        return 200, {}
    if event.get("thread_ts"):
        return 200, {}
    message = event.get("text", "")
    if not isinstance(message, str) or len(message) > 2000:
        return 200, {}
    if not is_change_intent(message):
        return 200, {}
    event_id = data.get("event_id", "")
    if not event_id or not is_new(event_id):
        return 200, {}
    thread_ts = event.get("ts", "")
    if thread_ts:
        try:
            received_at = datetime.fromtimestamp(float(thread_ts), tz=timezone.utc)
        except (TypeError, ValueError, OverflowError):
            return 200, {}
        threading.Thread(target=process_change,
                         args=(channel, thread_ts, event_id, message, received_at),
                         daemon=True).start()
    return 200, {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.respond(200, {"status": "ok", "mode": "facebook-enabled" if facebook.publishing_configured() else "preview-only", "version": "1.4"})
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
