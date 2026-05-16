import os
import requests
from google import genai

# Henter hemmelighetene trygt fra GitHubs system
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Firi API
FIRI_API_URL = "https://api.firi.com"

def hent_firi_kryptoer():
    """Henter spesifikke kryptovalutaer fra Firi sin offisielle API"""
    # Kryptovalutaer vi vil overvåke
    onskede_symboler = {"BTC", "XRP", "LTC", "ETH", "SOL", "ADA"}
    
    kryptoer = {}
    try:
        # Hent alle markeder og deres tickers fra Firi API (offentlig endpoint)
        response = requests.get(f"{FIRI_API_URL}/v2/markets/tickers", timeout=10)
        response.raise_for_status()
        tickers = response.json()
        
        # Filtrer for ønskede kryptovalutaer med NOK-prising
        for ticker in tickers:
            market = ticker.get("market", "")
            symbol = None
            if market.endswith("-NOK"):
                symbol = market.split("-")[0]
            elif market.endswith("NOK"):
                symbol = market[:-3]
            if symbol and symbol in onskede_symboler:
                bid = float(ticker.get("bid", 0) or 0)
                ask = float(ticker.get("ask", 0) or 0)
                siste = float(ticker.get("last", 0) or 0)
                volum = float(ticker.get("volume", 0) or 0)
                endring24h = float(ticker.get("change", 0) or 0)
                midtpris = (bid + ask) / 2 if (bid and ask) else siste or bid or ask
                spread_prosent = ((ask - bid) / bid * 100) if bid else 0

                kryptoer[symbol] = {
                    "market": market,
                    "pris": midtpris,
                    "bid": bid,
                    "ask": ask,
                    "siste": siste,
                    "volum": volum,
                    "endring24h": endring24h,
                    "spread_prosent": spread_prosent,
                }
    except Exception as e:
        print(f"Feil ved henting av Firi-data: {e}")
    
    return kryptoer

def kjor_robot():
    print("Starter PurrFolio robot...")
    
    # Hent kryptodata fra Firi sin offisielle API
    print("Henter kryptodata fra Firi...")
    kryptoer = hent_firi_kryptoer()
    
    # Forbered detaljert datatabell for AI-prompten
    if kryptoer:
        krypto_linjer = []
        for symbol, data in kryptoer.items():
            endring_str = f"{data['endring24h']:+.2f}%" if data['endring24h'] != 0 else "N/A"
            volum_str = f"{data['volum']:.4f}" if data['volum'] else "N/A"
            linje = (
                f"{symbol}: pris={data['pris']:.2f} NOK"
                f", siste={data['siste']:.2f} NOK"
                f", bid={data['bid']:.2f}"
                f", ask={data['ask']:.2f}"
                f", spread={data['spread_prosent']:.2f}%"
                f", 24h endring={endring_str}"
                f", volum={volum_str}"
            )
            krypto_linjer.append(linje)
        krypto_tekst = "Kryptovalutaer fra Firi:\n" + "\n".join(krypto_linjer)
    else:
        krypto_tekst = "Ingen kryptovalutaer funnet."

    print("Spør Google Gemini AI om analyse...")
    try:
        ai_klient = genai.Client(api_key=GEMINI_API_KEY)
        prompt = (
            f"Du er en kryptovaluta-analytiker. Her er sanntidsdata fra den norske børsen Firi:\n\n"
            f"{krypto_tekst}\n\n"
            f"For HVER kryptovaluta, gi en anbefaling på norsk med dette formatet:\n"
            f"[SYMBOL]: [KJØP / SELG / HOLD] — [én setning begrunnelse]\n\n"
            f"Basér anbefalingen på: 24h endring, spread (høy spread = dårlig likviditet), "
            f"og forholdet mellom bid og siste pris. "
            f"Ikke gi generelle råd om krypto som aktivaklasse. Vær konkret og kortfattet."
        )
        respons = ai_klient.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        ai_svar = respons.text
    except Exception as e:
        ai_svar = f"Kunne ikke hente AI-analyse. Feilmelding: {e}"

    # Forbered kompakt visning for Discord (én linje per mynt)
    krypto_visning = ""
    if kryptoer:
        for symbol, data in kryptoer.items():
            volum_str = f"{data['volum']:.4f}" if data['volum'] else "N/A"
            krypto_visning += (
                f"**{symbol}** — {data['pris']:.2f} NOK "
                f"(volum={volum_str}) "
                f"| spread {data['spread_prosent']:.2f}%\n"
            )
    else:
        krypto_visning = "Ingen data tilgjengelig."

    discord_melding = {
        "content": (
            f"🐱 **PurrFolio – Krypto oppdatering**\n\n"
            f"₿ **Markedsdata:**\n{krypto_visning}\n"
            f"🧠 **AI-anbefalinger:**\n{ai_svar}"
        )
    }

    print("Sender til Discord...")
    requests.post(DISCORD_WEBHOOK, json=discord_melding)
    print("✅ Suksess!")

if __name__ == "__main__":
    kjor_robot()
