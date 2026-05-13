import os
import requests
import yfinance as yf
from google import genai

# Henter hemmelighetene trygt fra GitHubs system
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def kjor_robot():
    print("Henter aksjedata...")
    # Henter kurser fra Yahoo Finance (Equinor på Oslo Børs = EQNR.OL)
    aksje = yf.Ticker("EQNR.OL")
    historikk = aksje.history(period="5d")
    
    siste_pris = historikk['Close'].iloc[-1]
    forrige_pris = historikk['Close'].iloc[-2]
    endring_prosent = ((siste_pris - forrige_pris) / forrige_pris) * 100

    print("Spør Google Gemini AI om analyse...")
    try:
        ai_klient = genai.Client(api_key=GEMINI_API_KEY)
        prompt = (f"Equinor (EQNR.OL) handles i dag for {siste_pris:.2f} NOK. "
                  f"Aksjen har endret seg med {endring_prosent:.2f}% siden i går. "
                  f"Gi en ekstremt kort vurdering på norsk (maks 2 setninger) om dette "
                  f"fremstår som en god kjøpsmulighet basert på ren prisutvikling.")
        
        respons = ai_klient.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        ai_svar = respons.text
    except Exception as e:
        ai_svar = f"Kunne ikke hente AI-analyse. Feilmelding: {e}"

    discord_melding = {
        "content": f"🐱 **PurrFolio oppdatering for Equinor (EQNR.OL)**\n"
                   f"📈 Siste pris: **{siste_pris:.2f} NOK** ({endring_prosent:+.2f}%)\n"
                   f"🧠 **AI-hjernen sier:** {ai_svar}"
    }

    print("Sender til Discord...")
    requests.post(DISCORD_WEBHOOK, json=discord_melding)
    print("Suksess!")

if __name__ == "__main__":
    kjor_robot()
