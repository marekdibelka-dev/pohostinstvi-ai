"""Safe Facebook Page photo publishing and Czech time-window policy.

Publishing requires FB_AUTO_PUBLISH=1, Meta Page credentials and a persistent SQLite DB.
No queued/stale posts: only messages received within allowed windows can publish.
"""
import io
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, time, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

PRAGUE = ZoneInfo('Europe/Prague')
WINDOWS = {4: (time(18), time(21)), 5: (time(18), time(21)), 6: (time(16), time(20))}


def allowed_at(dt):
    local = dt.astimezone(PRAGUE)
    window = WINDOWS.get(local.weekday())
    return bool(window and window[0] <= local.time().replace(tzinfo=None) < window[1])


def caption(change):
    return (f"🍺 NOVINKA NA ČEPU!\n\n"
            f"Právě jsme narazili {change['new']}!\n"
            f"Přijďte ochutnat. Cena: {change['price']} Kč.\n\n"
            "📍 Pohostinství Starojická Lhota\n"
            "Těšíme se na vás!")


def infographic(change):
    """Create original square PNG; adapt design after receiving brand reference."""
    from PIL import Image, ImageDraw, ImageFont
    canvas = Image.new('RGB', (1080, 1080), '#102D2A')
    draw = ImageDraw.Draw(canvas)
    try:
        regular = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        bold = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
        def font(n, heavy=False):
            return ImageFont.truetype(bold if heavy else regular, n)
    except OSError:
        def font(n, heavy=False):
            return ImageFont.load_default()
    draw.rectangle((35, 35, 1045, 1045), outline='#D9B66D', width=5)
    draw.rounded_rectangle((105, 100, 975, 225), radius=15, fill='#D9B66D')
    draw.text((540, 162), 'NOVINKA NA ČEPU', font=font(58, True), fill='#102D2A', anchor='mm')
    draw.text((540, 315), 'POHOSTINSTVÍ STAROJICKÁ LHOTA', font=font(29, True), fill='#F2E8CE', anchor='mm')
    name = change['new'].strip()
    if len(name) > 80:
        raise ValueError('Beer name too long for infographic')
    # Word wrapping based on actual rendered width; at most 3 lines.
    words = name.split()
    lines, line = [], ''
    for word in words:
        candidate = (line + ' ' + word).strip()
        if draw.textbbox((0, 0), candidate, font=font(72, True))[2] > 840 and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    if len(lines) > 3:
        raise ValueError('Beer name does not fit infographic')
    center = 530
    for i, txt in enumerate(lines):
        draw.text((540, center + (i-(len(lines)-1)/2)*100), txt,
                  font=font(72, True), fill='#FFFFFF', anchor='mm')
    draw.rounded_rectangle((315, 730, 765, 870), radius=25, fill='#D9B66D')
    draw.text((540, 800), f"{change['price']} Kč", font=font(82, True), fill='#102D2A', anchor='mm')
    draw.text((540, 962), 'PŘIJĎTE OCHUTNAT', font=font(38, True), fill='#F2E8CE', anchor='mm')
    buf = io.BytesIO()
    canvas.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def _connect(db_path):
    con = sqlite3.connect(db_path, timeout=10)
    con.execute('CREATE TABLE IF NOT EXISTS published_events ('
                'event_id TEXT PRIMARY KEY, status TEXT NOT NULL, '
                'created_at TEXT NOT NULL, post_id TEXT)')
    con.commit()
    return con


def claim_event(event_id, db_path):
    """Persistent, atomic claim. Failed/uncertain requests are NOT auto-retried."""
    with closing(_connect(db_path)) as con:
        cursor = con.execute('INSERT OR IGNORE INTO published_events '
                             '(event_id,status,created_at) VALUES (?,?,?)',
                             (event_id, 'processing', datetime.now(timezone.utc).isoformat()))
        con.commit()
        return cursor.rowcount == 1


def complete_event(event_id, db_path, status, post_id=None):
    with closing(_connect(db_path)) as con:
        con.execute('UPDATE published_events SET status=?,post_id=? WHERE event_id=?',
                    (status, post_id, event_id))
        con.commit()


def post_photo(change, token, page_id, api_version='v26.0'):
    """Publish one photo+caption via Meta Graph API multipart/form-data."""
    if not page_id.isdigit() or not api_version.startswith('v') or not api_version[1:].replace('.', '').isdigit():
        raise ValueError('Invalid Meta Page ID or API version')
    png = infographic(change)
    boundary = 'PohostinstviAIUploadBoundary'
    fields = [('caption', caption(change)), ('published', 'true')]
    parts = []
    for key, value in fields:
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n').encode())
    parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="source"; filename="pivo.png"\r\n'
                  'Content-Type: image/png\r\n\r\n').encode() + png + b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    req = Request(f'https://graph.facebook.com/{api_version}/{page_id}/photos',
                  data=b''.join(parts), method='POST', headers={
                      'Authorization': 'Bearer ' + token,
                      'Content-Type': f'multipart/form-data; boundary={boundary}',
                  })
    with urlopen(req, timeout=25) as response:
        result = json.load(response)
    if not result.get('id'):
        raise RuntimeError('Meta response missing photo ID')
    return result.get('post_id') or result['id']


def publishing_configured():
    db = os.getenv('FB_DB_PATH', '')
    return (os.getenv('FB_AUTO_PUBLISH') == '1'
            and bool(os.getenv('FB_PAGE_ID'))
            and bool(os.getenv('FB_PAGE_ACCESS_TOKEN'))
            and bool(db)
            and Path(db).parent.is_dir())
