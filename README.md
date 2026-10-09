# Pohostinství AI – cloudový Slack bot v1.3 (pouze náhled)

Tato verze přijímá zprávy od **všech lidských účastníků** kanálu určeného `SLACK_CHANNEL_ID`, rozpoznává několik běžných českých formulací a odpovídá návrhem výměny ve vlákně. **Nic nevytváří ani nemaže v Dotykačce, nemění web a nepublikuje na Facebooku.**

## Aktualizace již běžící verze v1.2

1. V GitHub repozitáři `marekdibelka-dev/pohostinstvi-ai` nahraď soubory `app.py`, `README.md`, `.env.example` a přidej `test_v13.py` ze složky v1.3. Ostatní soubory mohou zůstat stejné. V GitHubu klikni **Commit changes**.
2. Railway by mělo po commitu automaticky nasadit novou verzi. Ověř `https://web-production-7726f.up.railway.app/health`: `version` má být `1.3`, `mode` `preview-only`.
3. V Railway → Variables ponech `SLACK_CHANNEL_ID`, `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`. Starou proměnnou `SLACK_ALLOWED_USER_IDS` můžeš smazat; v1.3 ji ignoruje.
4. Slack bot musí zůstat členem kanálu a Event Subscriptions musí být aktivní.
5. Vyzkoušej příkaz od **jiného člena** kanálu. Bot má odpovědět ve vlákně.

## Podporované příklady

- `Došel Ogar Kazbek, narazil jsem Mazák 11°, cena 55 Kč.`
- `Došel Kazbek, dej tam Mazák 11 za 55.`
- `Narazili jsme Mazák místo Ogaru Kazbek. Cena 55 Kč.`
- `Vyměň Ogar Kazbek za Mazák 11°, 55 Kč.`
- `Kazbek je prázdný, místo něj máme Mazák jedenáctku za 55.`

Jde o **pravidlový parser, ne jazykový model**. Neporozumí každé volné formulaci; pokud není příkaz jednoznačný, požádá o upřesnění. Zatím neověřuje skutečné názvy produktů v Dotykačce, takže např. `Ogaru Kazbek` může být potřeba při ostrém napojení rozlišit od `Ogar Kazbek`. Pokud cena chybí, bot ji vyžádá. Před ostrým zápisem do Dotykačky bude nutné bezpečné párování produktů, perzistentní ochrana před duplicitami, audit a otestování zachování historie prodejů.

## Bezpečnost

- Slack HMAC podpis a pětiminutové časové okno; filtr na jediný kanál.
- Bot ignoruje vlastní zprávy a odpovědi ve vláknech.
- **Každý lidský uživatel s možností psát do kanálu může spustit náhled.** Doporučuje se změnit kanál na soukromý a spravovat členství.
- Žádné přístupy k Dotykačce, webu ani Facebooku.

## Test

`python -m unittest -v test_app.py test_v13.py`
