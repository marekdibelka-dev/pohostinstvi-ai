# Pohostinství Starojická Lhota — MASTER PROMPT / grafický standard v2.1

## Zadání pro AI
Profesionální reklamní pivní plakát 1080 × 1350 px pro Facebook/Instagram. Každá grafika je jedinečná a přesto zachovává stabilní identitu: fotografie reálného čepovaného piva, živé teplé hospodské světlo, dobře vyvážené kontrastní krémové letteringové titulky, červeno-zelené expresivní štětcové prvky, lesklé dřevo, jemné hop/barely motivy. Ne šablona, ne ilustrovaný hnědý podklad, ne obyčejný leták. Dominantní pivo + název + cena, nezahlcovat informacemi.

Zadaná data od obsluhy jsou jedinými povolenými zdroji veřejných faktů pro grafiku. Žádné neověřené ABV, IBU či chuťové charakteristiky. Originální logo je vložené až po generování AI, nikoli překreslené.

## Kritická technická pravidla
OpenAI image endpoint vytváří zdroj 1024×1536 (2:3), ale Instagram/Facebook chce 1080×1350 (4:5). Předchozí verze ořezávala zdroj o 128 px nahoře a dole a uřízla nápis „DNES NA ČEPU“. Od v2.1 se musí **vždy zachovat celý zdroj** a doplnit pouze postranní ambientní okraje. Nadpis vždy alespoň 7 % uvnitř zdrojové grafiky, stejně tak logo, texty a cenovka.

Nezávislý AI kontrolor musí vyhodnotit pravopis a úplnost textů, správnou cenu, zákaz nepodložených údajů, dostatečnou fotografickou kvalitu a zda žádný text není oříznutý. Pokud kontrola nedá požadované odpovědi, nepublikovat a vrátit chybu.

## Režim publikace
Pouze po výměně piva ve Slacku a jen pátek/sobota 18:00–21:00 a neděle 16:00–20:00 (Europe/Prague). Bez fronty mimo okno. Nezávislá skutečná otevírací doba: pátek/sobota 18:00–22:00; neděle 17:00–21:00. Dokud se nezkontroluje první živý obrázek v2.1, `FB_AUTO_PUBLISH=0`.
