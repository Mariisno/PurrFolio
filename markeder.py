"""Henter markedsdata: kryptovaluta fra Firi og aksjer/fond fra Yahoo Finance.

Modulen er delt mellom Discord-roboten (robot.py) og porteføljedashboardet
(dashbord.py), slik at prishenting bare finnes ett sted.
"""

FIRI_API_URL = "https://api.firi.com"

# Kryptovalutaene Discord-roboten overvåker som standard
STANDARD_KRYPTO = {"BTC", "XRP", "LTC", "ETH", "SOL", "ADA"}


def hent_firi_kryptoer(onskede_symboler=None):
    """Henter kryptovalutaer fra Firi sin offisielle API.

    Returnerer en dict på formen {symbol: {pris, bid, ask, siste, volum,
    endring24h, spread_prosent, market}}. Alle priser er i NOK.
    """
    import requests

    if onskede_symboler is None:
        onskede_symboler = STANDARD_KRYPTO
    onskede_symboler = {s.upper() for s in onskede_symboler}

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


def _les_hurtiginfo(hurtiginfo, *nokler):
    """Plukker første tilgjengelige nøkkel ut av yfinance sin fast_info."""
    for nokkel in nokler:
        try:
            verdi = hurtiginfo[nokkel]
        except Exception:
            verdi = getattr(hurtiginfo, nokkel, None)
        if verdi:
            return verdi
    return None


def hent_yahoo_kurser(tickere):
    """Henter siste kurs for aksjer, ETF-er og fond fra Yahoo Finance.

    Returnerer {ticker: {pris, forrige_slutt, endring24h, valuta}}. Prisen er i
    instrumentets egen handelsvaluta — omregning til NOK skjer i portefolje.py.
    Tickere som feiler hoppes over, slik at én død ticker ikke velter resten.
    """
    tickere = [t for t in dict.fromkeys(tickere) if t]
    if not tickere:
        return {}

    try:
        import yfinance
    except ImportError:
        print("Fant ikke yfinance — installer med: pip install yfinance")
        return {}

    kurser = {}
    for ticker in tickere:
        try:
            instrument = yfinance.Ticker(ticker)
            hurtiginfo = getattr(instrument, "fast_info", {})

            pris = _les_hurtiginfo(hurtiginfo, "last_price", "lastPrice", "regular_market_price")
            forrige_slutt = _les_hurtiginfo(
                hurtiginfo, "previous_close", "previousClose", "regular_market_previous_close"
            )
            valuta = _les_hurtiginfo(hurtiginfo, "currency") or "USD"

            # Faller tilbake på historikk hvis hurtiginfoen er tom
            if not pris:
                historikk = instrument.history(period="5d")
                if not historikk.empty:
                    sluttkurser = historikk["Close"].dropna()
                    if len(sluttkurser):
                        pris = float(sluttkurser.iloc[-1])
                    if not forrige_slutt and len(sluttkurser) > 1:
                        forrige_slutt = float(sluttkurser.iloc[-2])

            if not pris:
                print(f"Fant ingen kurs for {ticker}")
                continue

            pris = float(pris)
            forrige_slutt = float(forrige_slutt) if forrige_slutt else 0.0
            endring24h = ((pris - forrige_slutt) / forrige_slutt * 100) if forrige_slutt else 0.0

            kurser[ticker] = {
                "pris": pris,
                "forrige_slutt": forrige_slutt,
                "endring24h": endring24h,
                "valuta": str(valuta).upper(),
            }
        except Exception as e:
            print(f"Feil ved henting av {ticker}: {e}")

    return kurser


def hent_valutakurser(valutaer):
    """Henter vekslingskurs til NOK for hver valuta, f.eks. {'USD': 10.42}.

    NOK er alltid 1.0. Øvrige valutaer hentes som Yahoo-paret <VALUTA>NOK=X.
    """
    valutaer = {str(v).upper() for v in valutaer if v}
    kurser = {"NOK": 1.0}

    manglende = sorted(valutaer - {"NOK"})
    if not manglende:
        return kurser

    yahoo_par = {f"{valuta}NOK=X": valuta for valuta in manglende}
    for ticker, data in hent_yahoo_kurser(list(yahoo_par)).items():
        kurser[yahoo_par[ticker]] = data["pris"]

    return kurser
