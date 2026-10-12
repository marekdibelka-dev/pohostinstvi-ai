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
import random
import unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageFont
from ai_design import _api, _response_text, SIZE, BASE, research_beer

log=logging.getLogger(__name__)


def _fold(s):
    value=unicodedata.normalize('NFKD',str(s).lower())
    return ''.join(c for c in value if not unicodedata.combining(c))


def _literal_key(s):
    """Normalize case/spacing, but NEVER strip Czech diacritics.

    The old verifier folded 'ČEPU' to 'CEPU', allowing incorrect text.
    """
    s=unicodedata.normalize('NFC',str(s).casefold())
    return ''.join(c for c in s if c.isalnum())


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
    """Premium Czech ad art direction with hard source-canvas safe margins.

    The API makes a 1024x1536 image, while Facebook needs 1080x1350.
    Final processing FITS the full 2:3 source to 4:5; it must never crop text.
    """
    tint=(info.get('color') or 'bright natural golden to amber, not unnaturally brown')[:90]
    motifs=(info.get('visual_motifs') or 'realistic hops, golden barley, old Czech pub')[:130]
    required=[name,f'{price} Kč']+extras
    return (
        'Create a MASTERPIECE of Czech craft beer ADVERTISING ART, as polished as '
        'the best photographed brewery campaign for a high-end magazine. '
        'ART DIRECTION: photorealistic, cinematically lit, deep layered tavern '
        'interior in amber tungsten light, glistening real wooden bar, vivid '
        'luminous translucent fresh beer (not flat brown liquid), crisp bubbles '
        'and fine condensation, generous convincing foam. Warm bokeh lanterns '
        'and softly visible brass beer taps create depth. Fresh emerald green '
        'hops and golden barley in the foreground, not a flat plain muddy void. '
        'Bold asymmetrical sophisticated poster: hero beer glass on RIGHT half, '
        'expressive distressed large cream display serif lettering on LEFT, '
        'artfully layered dark forest-green and rich vermilion BRUSH STROKES '
        'under/behind select headlines, cinematic cast shadows, painterly '
        'textural accents, dramatic luminous reflections. More like real '
        'high-end commercial photo and handcrafted graphic design together '
        'than an old flat illustration or infographic. Strong dynamic '
        'hierarchy: first the beer name; then compelling foaming golden beer; '
        'then stupňovitost, then expressive big painted red price medallion. '
        'Carefully balance the bright glass and readable editorial text, '
        'no huge empty backgrounds, no UI boxes, no hard panel outlines, '
        'no cheap generic templates. Brand-consistent expressive palette '
        'of cream, golden straw, dark walnut, forest green and brick-red. '
        'The model must create the entire premium poster with gorgeous '
        'art-directed distressed Czech typography for beer name and price. '
        'A separate finishing pass WILL ADD an exact Czech heading, '
        'so DO NOT write, draw, allude to or place the headline yourself. '
        'Leave an elegantly art-directed dark green, red and warm wood banner '
        'zone in the upper-left x=6%-72%, y=5%-22%, with beautiful painterly '
        'texture but NO letters or symbols; the real headline is added there. '
        f'Beer visual color direction: {tint}. Accents: {motifs}. '
        f'The ONLY words/numbers permitted anywhere: {json.dumps(required,ensure_ascii=False)}. '
        'Render EXACTLY this Czech text with letter-perfect diacritics. '
        'DO NOT add any extra words, numeric claims, ABV, IBU, brewery marks, '
        'locations, historic claims, false beer labels, watermarks, or logos. '
        'IMPORTANT SOURCE CANVAS RULES for 1024x1536 portrait: '
        'Leave x=6%-72%, y=5%-22% completely free of lettering for an '
        'externally typeset Czech headline. Main beer title starts at '
        'y=29%-46%. Price medallion y=68%-84%. '
        'All visible letters, strokes, numerals and graphic badges MUST be '
        'at least 7% INSIDE all 4 edges of the SOURCE canvas. '
        'This is absolutely nonnegotiable: DO NOT crop any letter at the '
        'top, bottom, left or right. Include the whole foam cap and glass base. '
        'Reserve a clean top-right region x=74%-94%, y=12%-29% for '
        'a circular REAL pub logo added separately (draw no logo yourself). '
        'Place only text on the left, not across the glass. '
        'The final image will be fitted whole into a 4:5 social poster '
        'WITHOUT CROPPING, so design with strong safe margins and legible type. '
        'Crisp professional advertising photography, not cartoon, '
        'not brown illustration, no people.'
    )


def _add_exact_headline(im):
    """Draw guaranteed exact Czech headline after AI generation.

    This is an intentionally small fixed finishing layer, not a photo template:
    the AI still art-directs the main branded beer advertisement. Keeping the
    diacritic in a deterministic font avoids 'DNES NA CEPU' entirely.
    """
    im=im.convert('RGBA')
    w,h=im.size
    if (w,h)!=(1080,1350):
        raise ValueError('Unexpected canvas size for title layer')
    layer=Image.new('RGBA',(w,h),(0,0,0,0))
    d=ImageDraw.Draw(layer)
    rng=random.Random(2202)
    # Hand-painted green band with tapered, ragged edges. Opaque enough to
    # obscure any stray model-drawn letters in the reserved headline area.
    outline=[]
    for i in range(25):
        x=35+i*31
        outline.append((x,55+rng.randint(-11,10)))
    for i in reversed(range(25)):
        x=35+i*31
        outline.append((x,196+rng.randint(-10,12)))
    d.polygon(outline,fill=(8,47,29,255))
    for i in range(34):
        x=rng.randint(38,710); y=rng.choice([rng.randint(49,73),rng.randint(174,209)])
        d.line((x,y,x+rng.randint(15,100),y+rng.randint(-2,2)),fill=(7,40,29,180),width=rng.randint(1,4))
    # Red energetic brush below banner, not a generic rectangular box.
    for k in range(17):
        xa=53+rng.randint(0,12); ya=195+k//4+rng.randint(0,6)
        xb=785-rng.randint(0,85)
        d.line((xa,ya,xb,ya-14+rng.randint(-6,4)),fill=(175,35,27,rng.randint(165,230)),width=rng.randint(1,5))
    # Draw a scalable Czech-capable font; never silently fall back to bitmap.
    from ai_design import _font
    title='DNES NA ČEPU'
    font=None
    for sz in range(83,51,-1):
        f=_font(sz,'serif')
        box=d.textbbox((0,0),title,font=f,stroke_width=2)
        if box[2]-box[0]<=690:
            font=f
            break
    if font is None:
        raise RuntimeError('Czech headline cannot fit safely')
    x=78
    y=83
    d.text((x+3,y+4),title,font=font,fill=(0,0,0,165),stroke_width=2,stroke_fill=(0,0,0,130))
    d.text((x,y),title,font=font,fill=(255,232,176,255),stroke_width=1,stroke_fill=(62,37,14,255))
    return Image.alpha_composite(im,layer).convert('RGB')


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



def _fit_entire_source_to_4x5(source, final_size=SIZE):
    """Never delete any edge pixels, unlike v2.0's destructive center-crop.

    A full-height, aspect-ratio-preserved poster sits over a softened, extended
    version of the source, so the narrower 2:3 generation fills 4:5 safely.
    """
    src=source.convert('RGB')
    w,h=final_size
    if src.width<=0 or src.height<=0 or w<=0 or h<=0:
        raise ValueError('Invalid image dimensions')
    cover=ImageOps.fit(src,final_size,method=Image.Resampling.LANCZOS,centering=(.5,.5))
    cover=cover.filter(ImageFilter.GaussianBlur(36)).convert('RGBA')
    veil=Image.new('RGBA',final_size,(19,11,7,65))
    cover=Image.alpha_composite(cover,veil).convert('RGB')
    scale=min(w/src.width,h/src.height)
    fit_w=max(1,round(src.width*scale)); fit_h=max(1,round(src.height*scale))
    fitted=src.resize((fit_w,fit_h),Image.Resampling.LANCZOS)
    x=(w-fit_w)//2; y=(h-fit_h)//2
    if x==0 and y==0:
        return fitted
    # Soft fade only the outer 16px of the vertical edges; ALL SOURCE PIXELS
    # are preserved spatially with no destructive crop.
    mask=Image.new('L',(fit_w,fit_h),255)
    fade=min(14,max(0,(w-fit_w)//4))
    if fade:
        md=ImageDraw.Draw(mask)
        for k in range(fade):
            alpha=int(255*k/fade)
            md.line((k,0,k,fit_h),fill=alpha,width=1)
            md.line((fit_w-1-k,0,fit_w-1-k,fit_h),fill=alpha,width=1)
    cover.paste(fitted,(x,y),mask)
    return cover


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
          'visible_text (string), legible (boolean), premium_composition (boolean), '
          'edge_text_clipped (boolean), premium_photo_realism (boolean). '
          'edge_text_clipped MUST be true if ANY part of any letter/number is cut off by '
          'the image border. premium_composition false for generic layouts, '
          'premium_photo_realism false for illustration-like beer. '
          'Reject unreadable, deformed or fake beer labels. No markdown.')},
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
    if (data.get('legible') is not True or data.get('premium_composition') is not True
            or data.get('premium_photo_realism') is not True or data.get('edge_text_clipped') is not False):
        raise RuntimeError('Poster design or typographic legibility failed independent image review')
    seen=_literal_key(data.get('visible_text',''))
    for item in ['DNES NA ČEPU',name,str(price),'Kč',*extras]:
        if _literal_key(item) not in seen:
            raise RuntimeError('AI typography verification failed: exact Czech characters were missing')
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
        # Non-destructive 2:3 -> 4:5 layout; source artwork is NEVER cropped.
        # The former center-crop removed 128 original pixels from both ends,
        # clipping the 'DNES NA ČEPU' headline despite the QA pass.
        im=_fit_entire_source_to_4x5(im)
        im=_add_exact_headline(im)
        im=_add_exact_logo(im)
        _vision_quality_check(im,name,price,extra)
        buf=io.BytesIO();im.save(buf,format='PNG',optimize=True)
        return buf.getvalue(), info
