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
    """1080×1350 cinematic pub artwork with verified text and original venue logo.

    The beer glass is a crop of a user-supplied pub graphic, with no beer brand
    or political messaging. Product names and prices are always overlaid as
    deterministic text, never AI-rendered into the background.
    """
    import random
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

    name = str(change['new']).strip()
    price = int(change['price'])
    if not name or len(name) > 80 or not 1 <= price <= 1000:
        raise ValueError('Invalid beer name or price for infographic')
    assets = Path(__file__).resolve().parent / 'assets'
    logo_path = assets / 'logo_pohostinstvi.jpg'
    hero_path = assets / 'beer_hero.jpg'
    texture_path = assets / 'pub_texture.jpg'
    for asset in (logo_path, hero_path, texture_path):
        if not asset.is_file():
            raise FileNotFoundError(f'Missing graphic asset: {asset.name}')

    W, H = 1080, 1350
    with Image.open(texture_path) as bg:
        bg = bg.convert('RGB').resize((W,H), Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(65)).convert('RGBA')
    # Deep brown cinematic shade; all original poster lettering is illegible.
    shade = Image.new('RGBA', (W,H), (13,9,8,188))
    im = Image.alpha_composite(bg, shade)
    glow = Image.new('RGBA',(W,H),(0,0,0,0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((430,160,1350,1220),fill=(250,127,20,82))
    gd.ellipse((-380,720,480,1570),fill=(165,76,20,48))
    im = Image.alpha_composite(im, glow.filter(ImageFilter.GaussianBlur(160)))

    # The hero pint is photographic, not drawn. Feather edges into the bokeh.
    with Image.open(hero_path) as photo:
        hero = photo.convert('RGB').resize((480,865), Image.Resampling.LANCZOS)
    mask = Image.new('L',hero.size,0)
    md=ImageDraw.Draw(mask)
    md.rounded_rectangle((40,4,478,858),radius=45,fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(36))
    # Feather the photo on every edge so it never ends in a rectangular seam.
    pix=mask.load()
    for yy in range(hero.height):
        fade_y=min(1.0, yy/85.0, (hero.height-1-yy)/110.0)
        for xx in range(hero.width):
            fade_x=min(1.0, xx/105.0, (hero.width-1-xx)/45.0)
            pix[xx,yy]=int(pix[xx,yy]*max(0.0,min(fade_x,fade_y)))
    im.paste(hero,(618,325),mask)

    # Painted strokes with irregular tapered edges, not box-like UI panels.
    paint=Image.new('RGBA',(W,H),(0,0,0,0)); pd=ImageDraw.Draw(paint)
    rng=random.Random(425)
    def brush(x1,y1,x2,y2,color):
        poly=[(x1+12,y1+11),(x2-45,y1-8),(x2+12,y1+18),
              (x2-4,y2-13),(x2-55,y2+10),(x1-18,y2-7)]
        pd.polygon(poly,fill=color)
        for _ in range(26):
            yy=rng.randrange(y1,y2)
            xa=rng.randrange(x1-18,x1+50)
            xb=rng.randrange(x2-90,x2+16)
            pd.line((xa,yy,xb,yy-rng.randrange(0,8)),fill=color,width=rng.randrange(1,6))
    brush(35,80,1010,255,(185,32,24,248))
    brush(46,858,626,1047,(183,25,24,242))
    im=Image.alpha_composite(im,paint)
    d=ImageDraw.Draw(im)
    cream='#FFF1D6'; gold='#FFD777'; shadow='#170b08'
    font_dir=Path('/usr/share/fonts/truetype/dejavu')
    def ft(n,kind='condensed'):
        filename={'condensed':'DejaVuSansCondensed-Bold.ttf',
                  'bold':'DejaVuSans-Bold.ttf',
                  'serif':'DejaVuSerifCondensed-Bold.ttf'}[kind]
        try: return ImageFont.truetype(str(font_dir/filename),n)
        except OSError: return ImageFont.load_default()
    def centered(text,y,sz,maxw,x=520,kind='condensed',fill=cream,stroke=2):
        while sz>24:
            font=ft(sz,kind)
            bbox=d.textbbox((0,0),text,font=font,stroke_width=stroke)
            if bbox[2]-bbox[0]<=maxw: break
            sz-=2
        d.text((x,y),text,font=font,anchor='mm',fill=fill,stroke_width=stroke,stroke_fill=shadow)
    centered('DNES NA ČEPU',167,91,945,x=520,kind='serif')
    # Strong, editorial beer title on the left, with adaptive line breaking.
    words=name.upper().split()
    def wrap(font, maxw):
        lines=[]; line=''
        for word in words:
            test=(line+' '+word).strip()
            if line and d.textbbox((0,0),test,font=font)[2]>maxw:
                lines.append(line); line=word
            else: line=test
        if line: lines.append(line)
        return lines
    chosen=None
    for size in (86,80,74,68,62,56,50,44,38):
        f=ft(size)
        lines=wrap(f,575)
        if len(lines)<=5 and all(d.textbbox((0,0),s,font=f)[2]<=575 for s in lines):
            chosen=(f,lines,size);break
    if chosen is None: raise ValueError('Beer name too long for graphic')
    font,lines,size=chosen
    d.text((70,342),'PIVNÍ NOVINKA',font=ft(34),fill=gold,stroke_width=1,stroke_fill=shadow)
    y=420
    for line in lines:
        d.text((65,y),line,font=font,fill=cream,stroke_width=3,stroke_fill=shadow)
        y+=size+19
    if y<760:
        d.line((70,y+18,525,y+18),fill='#D8A34B',width=7)
    centered(f'{price} Kč',947,135,535,x=328,kind='serif',fill=cream)
    d.text((88,1083),'PŘIJĎTE OCHUTNAT',font=ft(35),fill=gold,stroke_width=2,stroke_fill=shadow)
    # Original supplied logo; never synthesize lettering or redraw the emblem.
    with Image.open(logo_path) as original:
        logo=original.convert('RGB').resize((198,198),Image.Resampling.LANCZOS)
    circle=Image.new('L',logo.size,0)
    ImageDraw.Draw(circle).ellipse((1,1,196,196),fill=255)
    im.paste(logo,(441,1138),circle)
    # Footer separator helps distinguish venue branding from the beer title.
    d=ImageDraw.Draw(im)
    d.line((120,1315,408,1315),fill='#BB8B4D',width=3)
    d.line((672,1315,960,1315),fill='#BB8B4D',width=3)
    out=io.BytesIO()
    im.convert('RGB').save(out,format='PNG',optimize=True)
    return out.getvalue()

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
    from ai_design import create_poster
    # Publishing uses fresh AI imagery, never the offline static fallback.
    png, info = create_poster(change)
    # AI generation may take minutes; never publish after the window closes.
    if not allowed_at(datetime.now(timezone.utc)):
        raise RuntimeError('Publishing window closed during AI image generation')
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
            and bool(os.getenv('OPENAI_API_KEY'))
            and bool(db)
            and Path(db).parent.is_dir())
