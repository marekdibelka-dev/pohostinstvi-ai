# Pohostinství AI 2.0 — prémiové AI plakáty

**Změna architektury:** Výchozí režim `AI_DESIGN_MODE=full_poster` generuje **celou reklamní grafiku včetně kreativní typografie** pomocí OpenAI Images API. Je to zásadní rozdíl oproti starým verzím, které generovaly jen fotografii a následně kreslily jednoduchou šablonu v Pillow.

Pohostinství AI pak vloží **originální logo** ze souboru `assets/logo_pohostinstvi.jpg` a provede **nezávislou kontrolu** plakátu pomocí obrazového modelu. Kontroluje alespoň existenci a čitelnost názvu piva, ceny, nadpisu, nežádoucí číselné údaje a základní vizuální kvalitu. Při nesrovnalosti **nezveřejňuje**, ale vrátí chybu. Automatická kontrola však není zárukou 100% bezchybnosti; před produkčním provozem nutné vizuální testování několika reálných plakátů.

## Grafický standard
- 1080 × 1350 px, tmavá teplá filmová atmosféra, originální čepované pivo, texturované pozadí a propracovaná kompozice
- výrazná typografie, ručně působící červené a zelené tahy, skutečné pivovarské reklamní výtvarno
- AI dostává pouze název, stupňovitost a cenu od obsluhy; jiné neověřené hodnoty (IBU, ABV aj.) nesmí generovat
- Originální logo nikdy nevytváří AI; vloží se přesně ze souboru

## Railway
Nahrát **obsah rozbaleného ZIPu** do GitHub repozitáře ve větvi `main`, včetně nového `poster_ai.py` a původní složky `assets`.
Proměnné `OPENAI_API_KEY`, `FB_PAGE_ID`, `FB_PAGE_ACCESS_TOKEN`, `FB_DB_PATH` ponechat; `FB_AUTO_PUBLISH=0` ponechat do otestování. Nová volitelná proměnná `AI_DESIGN_MODE=full_poster` je výchozí, takže ji není nutné zakládat. `AI_IMAGE_QUALITY=high` je výchozí a může spotřebovat více kreditu; při potřebě úspor lze snížit na `medium` na úkor kvality. Generování i obrazová kontrola využívají placené API.

Test bez zveřejnění v Railway Console: spustit `/opt/venv/bin/python`, poté:

```python
from ai_design import create_poster
p, info = create_poster({'new': 'Mazák 11°', 'price': 55})
open('/data/test_mazak_v20.png', 'wb').write(p)
```

> **Pozor:** Náhled `preview/vizualni_koncept.png` pochází z grafického zadání a nástroje generování obrázků v ChatGPT. Není to skutečný výstup ještě neotestovaného režimu `full_poster` v Railway. Ten je nutné ověřit novým testem.

## Co se nemění
- Soukromý Slack `#piva-na-cepu` a příjem hlášení výměn piv od členů kanálu
- Čas publikace pouze pá/so 18–21, ne 16–20 (Europe/Prague), mimo čas bez fronty
- Otevírací doba pá/so 18–22, ne 17–21
- FB automaticky stále vypnut, dokud neproběhnou živé testy
- Dotykačka a web stále nejsou automaticky napojené

## Záložní režim
`AI_DESIGN_MODE=hybrid` ponechává technickou variantu fotografie + programové sazby z předchozích verzí. Automatické přepnutí při chybě **neexistuje** — při selhání je zveřejnění zablokováno.

Lokální testy: `python -m unittest discover -v`.
