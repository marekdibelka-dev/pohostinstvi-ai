"""Experimental full-art-direction poster creation with fail-closed text checks.

The image model designs the FULL visual campaign, not a photo to which a flat
Pillow template is added. The venue's ORIGINAL logo is composited afterward.
Never publish if text verification fails; never fall back to an unsafe poster.
"""
import base64
import io
import json
import logging
import os
import re
import unicodedata
from pathlib import Path
from PIL import Image, ImageDraw
from ai_design import _api, _response_text, SIZE, BASE, research_beer

log=logging.getLogger(__name__)


def _fold(s):
    value=unicodedata.normalize('NFKD',str(s).lower())
    return ''.join(c for c in value if not unicodedata.combining(c))


def _strip(s):
    s=unicodedata.normalize('NFKD',str(s).lower())
    s=''.join(c for c in s if not unicodedata.combining(c))
    return ''.join(c for c in s if c.isalnum())


def _copy(change):
    name=str(change.get('new') or '').strip()
    if not name or len(name)>75 or '\n' in name:
        raise ValueError('Invalid beer name for full-poster artwork')
    price=change.get('price')
    if isinstance(price,bool) or not str(price).isdigit() or not (1<=int(price)<=1000):
        raise ValueError('Invalid beer price')
    extra=[]
    for key in ('brewery','style'):
        v=str(change.get(key) or '').strip()
        if v:
            if len(v)>50 or '\n' in v: raise ValueError('Invalid optional beer fact')
            extra.append(v)
    return name,int(price),extra


def _make_prompt(name,price,extras,info):
    # Research may suggest color or props but cannot add numerical/factual copy.
    tint=(info.get('color') or 'golden amber unless a named beer style implies otherwise')[:90]
    props=(info.get('visual_motifs') or 'green hops, golden barley, old Czech pub')[:130]
    required=['DNES NA ČEPU',name,f'{price} Kč']+extras
    return (f'Art-direct and FINISH a polished premium vertical Czech craft beer '\
        f'advertising POSTER, not a plain photo or a digital infographic. '
        f'The visual feel is a warm photorealistic beverage campaign by an '\
        f'experienced brewery design studio, with expressive vintage editorial '\
        f'typography integrated artfully into the scene: distressed cream lettering, '\
        f'energetic real-paint brick-red and forest-green brush strokes, touches '\
        f'of warm brass-gold. A single natural delicious Czech beer in a realistic '\
        f'glowing foamy condensation-covered glass occupies RIGHT half, with '\
        f'wooden pub bar, hops and barley in the foreground, cinematic amber '\
        f'tungsten bokeh, high-end believable commercial lighting and strong depth. '\
        f'Put the LARGE impressive beer name on left with dramatic typographic '\
        f'hierarchy and legible bold prices on an expressive painted seal at bottom '\
        f'left. This should visually resemble a beautiful bespoke illustrated '\
        f'photo advertisement, NOT a UI panel, generic Canva template, or black '\
        f'background with flat words. Rich balanced details and deliberate '
        f'negative space. Beer visual color: {tint}. Brewery visual motifs: {props}. '
        f'Only render the following exact UTF-8 Czech copy in the poster, each '\
        f'legible and spelled letter-perfect with the exact diacritics: '\
        f'{json.dumps(required, ensure_ascii=False)}. '
        f'Use all items, but DO NOT add other words, numbers, percentage, ABV, '\
        f'IBU, tasting notes, fake labels, fabricated historical details, '\
        f'fake brewery logos or brand marks. Design the upper-right corner '\
        f'as a clear clean space for the ORIGINAL venue seal which is composited '\
        f'later, so do not invent or display any venue logo. '
        f'Portrait 4:5 SAFE COMPOSITION: source is 2:3 ratio and will be center-cropped '\
        f'to 4:5. Keep ALL text and essential details entirely within central '\
        f'83% of image HEIGHT (y=10% to 90%), and allow logo at upper right '\
        f'within the central region. Detailed expert food photography, no people, '\
        f'visually arresting but uncluttered, suitable for Facebook and Instagram.')


def _add_exact_logo(im):
    path=BASE/'assets'/'logo_pohostinstvi.jpg'
    if not path.is_file(): raise FileNotFoundError('Original Pohostinstvi logo missing')
    im=im.convert('RGBA')
    with Image.open(path) as source:
        raw=source.convert('RGB')
        side=min(raw.size); x=(raw.width-side)//2;y=(raw.height-side)//2
        logo=raw.crop((x,y,x+side,y+side)).resize((238,238),Image.Resampling.LANCZOS)
    mask=Image.new('L',(238,238),0)
    ImageDraw.Draw(mask).ellipse((1,1,236,236),fill=255)
    # Opaque original seal hides any spurious AI details at the chosen location.
    im.paste(logo,(806,30),mask)
    return im.convert('RGB')


def _vision_quality_check(image,name,price,extras):
    """Fail closed when a vision pass cannot confirm required exact visible text.

    This is a conservative check, not mathematically perfect proofreading. Our
    auto-publisher must stay off until real-world examples are visually reviewed.
    """
    bio=io.BytesIO(); image.save(bio,format='JPEG',quality=84)
    b64=base64.b64encode(bio.getvalue()).decode('ascii')
    r=_api('responses',{
      'model':os.getenv('AI_POSTER_QA_MODEL','gpt-4.1-mini'),
      'input':[{'role':'system','content':('You are a strict independent Czech poster proofreader. '
          'Visually transcribe all words and numbers that ACTUALLY appear. '
          'Never supply expected words that are not visible. '
          'Do not silently fix misspellings. Respond as a single JSON object with keys '
          'visible_text (string), legible (boolean), premium_composition (boolean). '
          'legible must be false if any headline or price is distorted or tiny. '
          'premium_composition must be false for generic layouts, obvious deformation, '
          'fake beer labels or low quality visual work. No markdown.')},
          {'role':'user','content':[
            {'type':'input_text','text':f'Transcribe and assess the photo poster. The source name and price to CHECK, not assume: {name!r}, {price} Kč. Additional copy: {extras!r}.'},
            {'type':'input_image','image_url':'data:image/jpeg;base64,'+b64,'detail':'high'}]}],
      'max_output_tokens':450,
    },timeout=95)
    raw=_response_text(r).strip()
    if raw.startswith('```'):
        raw=re.sub(r'^```(?:json)?\s*|\s*```$','',raw)
    try: data=json.loads(raw)
    except (ValueError,TypeError) as exc: raise RuntimeError('Poster proofreading did not return valid JSON') from exc
    if data.get('legible') is not True or data.get('premium_composition') is not True:
        raise RuntimeError('Poster design or typographic legibility failed independent image review')
    seen=_strip(data.get('visible_text',''))
    for item in ['DNES NA ČEPU',name,str(price),'Kč',*extras]:
        if _strip(item) not in seen:
            raise RuntimeError('AI typography verification failed: required copy was not legible')
    # Check there are no unexpected digits (fake ABV / IBU etc).
    detected=set(re.findall(r'\d+',unicodedata.normalize('NFKD',str(data.get('visible_text','')))))
    allowed=set(re.findall(r'\d+',' '.join([name,str(price),*extras])))
    if not detected.issubset(allowed):
        raise RuntimeError('Poster contains an unsupported numerical claim')
    # The original venue seal adds the venue words. No other public copy is
    # authorized unless explicitly supplied with the change.
    allowed_copy='DNES NA ČEPU '+name+' '+str(price)+' Kč '+(' '.join(extras))+' POHOSTINSTVÍ STAROJICKÁ LHOTA'
    allowed_words=set(re.findall(r'[a-z0-9]+',_fold(allowed_copy)))
    visible_words=set(re.findall(r'[a-z0-9]+',_fold(str(data.get('visible_text','')))))
    extras_seen={x for x in visible_words if len(x)>1 and x not in allowed_words}
    if extras_seen:
        raise RuntimeError('Poster contains unsupported words outside authorized copy')


def create_full_poster(change):
    name,price,extra=_copy(change)
    info=research_beer(name)
    prompt=_make_prompt(name,price,extra,info)
    r=_api('images/generations',{
        'model':os.getenv('AI_IMAGE_MODEL','gpt-image-1'),
        'quality':os.getenv('AI_IMAGE_QUALITY','high'),
        'size':'1024x1536','output_format':'png','prompt':prompt,
    },timeout=200)
    raw=base64.b64decode(r['data'][0]['b64_json'],validate=True)
    with Image.open(io.BytesIO(raw)) as generated:
        im=generated.convert('RGB')
        w,h=im.size
        # Crop central 4:5 poster from 2:3 source, then resize to final exact pixel size.
        new_h=min(h,round(w*5/4))
        top=max(0,(h-new_h)//2)
        im=im.crop((0,top,w,top+new_h)).resize(SIZE,Image.Resampling.LANCZOS)
        im=_add_exact_logo(im)
        _vision_quality_check(im,name,price,extra)
        buf=io.BytesIO();im.save(buf,format='PNG',optimize=True)
        return buf.getvalue(), info
