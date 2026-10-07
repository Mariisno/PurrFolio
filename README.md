# 🐱 PurrFolio

To ting i samme repo:

1. **Discord-roboten** (`robot.py`) — henter kryptokurser fra [Firi](https://firi.com),
   ber Google Gemini om en kort analyse på norsk, og poster den i Discord.
2. **Porteføljedashbordet** (`dashbord.py`) — en lokal webside som viser alle
   investeringene dine med live kurser, verdi i NOK, fordeling og gevinst/tap.

## Kom i gang med dashbordet

```bash
pip install -r requirements.txt
cp portefolje.eksempel.json portefolje.json   # fyll inn dine egne tall
python dashbord.py
```

Dashbordet åpner seg på <http://127.0.0.1:8000> og oppdaterer kursene hvert
30. sekund. Serveren lytter bare på 127.0.0.1, så tallene dine forlater aldri
maskinen — og `portefolje.json` er i `.gitignore`, så den havner ikke i git.

Nyttige valg:

| Valg | Betydning |
| --- | --- |
| `--port 9000` | Kjør på en annen port |
| `--fil /sti/til/portefolje.json` | Bruk en annen porteføljefil |
| `--buffer 60` | Mellomlagre kursene lenger (sekunder) |
| `--ingen-nettleser` | Ikke åpne nettleseren automatisk |

## Porteføljefilen

`portefolje.json` er en liste med beholdninger du redigerer selv. Endringer
plukkes opp med én gang — du trenger ikke å starte serveren på nytt.

```json
{
  "beholdninger": [
    {"symbol": "BTC", "navn": "Bitcoin", "type": "Krypto", "kilde": "firi", "antall": 0.015, "snittpris": 950000},
    {"symbol": "EQNR.OL", "navn": "Equinor", "type": "Aksjer og fond", "kilde": "yahoo", "antall": 40, "snittpris": 271.5},
    {"symbol": "AAPL", "navn": "Apple", "type": "Aksjer og fond", "kilde": "yahoo", "antall": 8, "snittpris": 195.2, "valuta": "USD"}
  ]
}
```

| Felt | Betydning |
| --- | --- |
| `symbol` | Kryptosymbol på Firi (`BTC`) eller Yahoo-ticker (`EQNR.OL`, `AAPL`) |
| `navn` | Navnet som vises i dashbordet |
| `type` | Gruppen posten havner i, f.eks. `Krypto` eller `Aksjer og fond` |
| `kilde` | `firi` for krypto, `yahoo` for aksjer, ETF-er og fond |
| `antall` | Hvor mange enheter du eier |
| `snittpris` | Snittpris per enhet, i samme valuta som instrumentet handles i |
| `valuta` | Valgfritt. Settes bare når instrumentet ikke handles i NOK (f.eks. `USD`) |

Poster uten kurs blir stående i tabellen som «ingen kurs» og holdes utenfor
totalen, med en merknad øverst — én ticker som feiler velter ikke resten.

## Sånn regnes tallene

- **Krypto** prises til midtpris mellom bid og ask fra Firi, i NOK.
- **Aksjer og fond** prises til siste kurs fra Yahoo Finance, omregnet til NOK
  med dagens vekslingskurs (`USDNOK=X` og tilsvarende).
- **Siste døgn** er endringen fra Firis 24-timerstall for krypto, og fra
  gårsdagens sluttkurs for aksjer.
- **Gevinst** er verdi minus kostpris. Kostprisen regnes om med *dagens*
  vekslingskurs, så for utenlandske poster er valutaeffekten en tilnærming.

## Discord-roboten

```bash
GEMINI_API_KEY=<nøkkel> DISCORD_WEBHOOK=<url> python robot.py
```

I GitHub Actions ligger nøklene som repository secrets, og
`.github/workflows/run_bot.yml` kan startes manuelt med *Run workflow*.
