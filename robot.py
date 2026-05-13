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
                bid = float(ticker.get("bid", 0))
                ask = float(ticker.get("ask", 0))
                last_price = (bid + ask) / 2 if (bid and ask) else bid or ask
                
                kryptoer[symbol] = {
                    "market": market,
                    "pris": last_price,
                    "bid": bid,
                    "ask": ask
                }
    except Exception as e:
        print(f"Feil ved henting av Firi-data: {e}")
    
    return kryptoer

def kjor_robot():
    print("Starter PurrFolio robot...")
    
    # Hent kryptodata fra Firi sin offisielle API
    print("Henter kryptodata fra Firi...")
    kryptoer = hent_firi_kryptoer()
    
    # Forbered data for Gemini
    krypto_tekst = ""
    if kryptoer:
        krypto_tekst = "Kryptovalutaer fra Firi:\n"
        for symbol, data in kryptoer.items():
            krypto_tekst += f"- {symbol}: {data['pris']:.2f} NOK\n"
    else:
        krypto_tekst = "Ingen kryptovalutaer funnet."

    print("Spør Google Gemini AI om analyse...")
    try:
        ai_klient = genai.Client(api_key=GEMINI_API_KEY)
        prompt = (f"Analyser disse kryptovalutaene:\n\n"
                  f"{krypto_tekst}\n"
                  f"Gi en ekstremt kort vurdering på norsk (maks 3 setninger) om disse "
                  f"fremstår som gode kjøpsmuligheter basert på prisutvikling.")
        
        respons = ai_klient.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        ai_svar = respons.text
    except Exception as e:
        ai_svar = f"Kunne ikke hente AI-analyse. Feilmelding: {e}"

    # Bygn Discord-melding
    discord_melding = {
        "content": f"🐱 **PurrFolio - Krypto oppdatering**\n\n"
                   f"₿ **Kryptovalutaer:**\n{krypto_tekst}\n"
                   f"🧠 **AI-analyse:**\n{ai_svar}"
    }

    print("Sender til Discord...")
    requests.post(DISCORD_WEBHOOK, json=discord_melding)
    print("✅ Suksess!")

if __name__ == "__main__":
    kjor_robot()
