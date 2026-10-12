# Pohostinství AI Cloud v1.7 – prémiová AI grafika

## Oprava náhledu podle MASTER PROMPTU

Soubor `preview/Pohostinstvi_AI_v1_7_nahled.png` ukazuje schválený **filmový reklamní styl** (nejde o starý šablonový náhled). Jde o výtvarnou referenci; samotný generátor produkuje vždy novou AI scénu a skládá do ní správné názvy, ceny a originální logo. V referenčním obrázku mohou být AI doplněné popisné detaily; neslouží jako podklad pro tvrzení o parametrech piva.

## Změna oproti v1.6

Každá nová zpráva o výměně piva ve Slacku vyvolá **novou AI fotografickou scénu** pro konkrétní pivo. Vizuální identita je stálá: tmavé hospodské prostředí, teplé nasvícení, sklenice vpravo, typografie vlevo, teplé zlaté a červené akcenty a originální logo Pohostinství Starojická Lhota.

- **1080×1350 px (4:5)**; bez chybně vykreslených cen, názvů a loga: ty se přidávají až po generování obrázku, deterministicky přes Pillow.
- Základní AI průzkum používá OpenAI Responses API s nástrojem `web_search`. Pokud není dohledatelný věrohodný zdroj, neuvádí další faktické parametry. AI průzkum slouží pro vizuální inspiraci; neověřené ABV/IBU se nikdy nepíšou do obrázku ani popisku.
- Text příspěvku zůstává jednoduchý a používá jen název a cenu ze Slacku. Pivovar a styl z výzkumu nejsou automaticky považovány za ověřené pro veřejný text.
- **Originální logo** je v `assets/logo_pohostinstvi.jpg`. Nenahrazujte ho AI verzí.
- AI obrázek je generován bez textu, etiket a log. Přesto je před plným spuštěním potřeba vizuální test, protože model může někdy vytvořit nežádoucí znaky.
- Při selhání AI nebo chybějícím API klíči se **nic nepublikuje**. Automatické opakování se neprovádí.

## Railway nastavení

1. Nahraj všechny soubory z této složky do kořene GitHub repozitáře aplikace (ponech stávající Slack secrets).
2. Nastav `OPENAI_API_KEY` v Railway Variables. **Klíč nikdy neposílej do chatu ani do GitHubu.** Generování obrázků a webový průzkum mohou být zpoplatněné zvlášť od předplatného ChatGPT.
3. Ponech `FB_PAGE_ID=849555404896594`, `FB_PAGE_ACCESS_TOKEN` a `FB_AUTO_PUBLISH=0`.
4. Pro bezpečné deduplikování je nutný Railway Volume připojený na `/data` a `FB_DB_PATH=/data/pohostinstvi_ai.sqlite3`.
5. Ověř platnost Page tokenu a Meta oprávnění `pages_manage_posts`.
6. Po kontrolovaném testu publikování a vizuální kontroly teprve přepni `FB_AUTO_PUBLISH=1`.

## Ostatní provozní pravidla

- Slack kanál `#piva-na-cepu` zůstává soukromý; všichni jeho členové mohou zadat výměnu.
- Zveřejnění pouze **pátek/sobota 18:00–21:00, neděle 16:00–20:00** (Europe/Prague), mimo okna žádná fronta.
- Běžná otevírací doba: **pátek/sobota 18:00–22:00, neděle 17:00–21:00**. Časy publikování nejsou totožné s otevírací dobou.
- Dotykačka, web a Instagram zatím nejsou tímto balíčkem napojené. Výměna produktu v Dotykačce se neprovádí.
- Automaticky se zpracují pouze zprávy se starým pivem, novým pivem a cenou, které odpovídají stávajícím pravidlům parseru.
- Facebook automatizace je výchozím nastavením **vypnutá**.

## Testy

`python -m unittest discover -v`
