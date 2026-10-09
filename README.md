# Pohostinství AI – cloudový Slack bot v1.2 (pouze náhled)

Tato verze **nemá přístup k Dotykačce, webu ani Facebooku**. Po zprávě v kanálu `#piva-na-cepu` pouze odpoví do vlákna návrhem výměny. Žádné mazání neprovádí.

## Nasazení

1. Vytvoř soukromý repozitář GitHub a nahraj do jeho kořene všechny soubory z této složky (bez `.env` a bez tajných klíčů).
2. V Railway otevři **New Project → Deploy from GitHub repo**, vyber repozitář.
3. V Railway → služba → **Variables** nastav hodnoty ze souboru `.env.example` (skutečné tajné hodnoty nezapisuj do repozitáře):
   - `SLACK_SIGNING_SECRET`: v https://api.slack.com/apps → tvoje Slack app → Basic Information → App Credentials → Signing Secret.
   - `SLACK_BOT_TOKEN`: Slack app → OAuth & Permissions → Bot User OAuth Token (`xoxb-...`).
   - `SLACK_CHANNEL_ID=C0C8Q0TDF0Q`.
   - `SLACK_ALLOWED_USER_IDS=U0C7PBSEDBM` (zatím pouze vlastník; další schválené uživatele přidávej čárkou).
4. Railway → **Settings → Networking → Generate Domain**. Otevři `https://<doména>/health`; odpověď má obsahovat `"mode":"preview-only"`.
5. Pokud Slack app ještě nemáš, vytvoř ji na https://api.slack.com/apps → **Create New App → From scratch**, zvol workspace **Lhocani**. V **OAuth & Permissions** přidej bot scopes `chat:write` a `channels:history` (pro soukromý kanál také `groups:history`), poté **Install to Workspace**. V kanálu `#piva-na-cepu` pozvi bota přes `/invite @jméno-bota`.
6. Ve Slack app → **Event Subscriptions** zapni Enable Events, Request URL nastav na `https://<doména>/slack/events` a v **Subscribe to bot events** přidej `message.channels` (pro soukromý kanál `message.groups`). Ulož; případně znovu nainstaluj app do workspace.
7. Pošli do Slacku: `Došel Ogar Kazbek, narazil jsem Mazák 11°, cena 55 Kč.` Bot by měl automaticky odpovědět **ve vlákně**. Původní testovací zpráva se znovu nezpracuje.

**Pozor:** propojení Slacku s ChatGPT **není totéž** jako vytvoření samostatné Slack app pro Railway. K nepřetržitému provozu je potřeba výše uvedená Slack app a její dva tajné údaje.

## Bezpečnost

- Ověření podpisu Slacku (HMAC SHA-256) a času požadavku ±5 minut.
- Povoleny jen zprávy z jednoho kanálu a od vybraných uživatelů; ve výchozím stavu pouze vlastník.
- Bot nereaguje na své zprávy, úpravy zpráv ani odpovědi ve vlákně.
- Jednoduché potlačení duplicitních eventů v paměti (po restartu se resetuje; pro ostré mazání musí být trvalé).
- Není zde žádný kód pro zápis nebo mazání v Dotykačce.
- Zatím není řešeno trvalé úložiště, workflow potvrzování ani automatická aktualizace webu či Facebooku.
- Pro ostrý provoz bude potřeba databáze, fronta úloh, idempotence, audit, oprávnění a ověření historie prodejů v Dotykačce.

## Lokální test

`python -m unittest -v test_app.py` (bez dalších knihoven)

## Připravená ukázka

Zpráva: `Došel Ogar Kazbek, narazil jsem Mazák 11°, cena 55 Kč.`

Odpověď: „Smazat produkt: Ogar Kazbek; Nové pivo: Mazák 11°; Cena: 55 Kč; TESTOVACÍ REŽIM – NIC NEPROVEDENO.“
