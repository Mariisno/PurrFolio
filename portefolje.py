"""Leser porteføljefilen og regner ut verdier, gevinst og fordeling.

Beholdningene ligger i portefolje.json (se portefolje.eksempel.json). Filen
redigerer du selv — roboten kobler seg ikke til kontoen din.
"""

import json
import os
from datetime import datetime, timezone

import markeder

STANDARD_FIL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portefolje.json")

# Kilder vi vet hvordan vi skal prise
KILDER = {"firi", "yahoo"}


class PortefoljeFeil(Exception):
    """Kastes når porteføljefilen mangler eller er feil satt opp."""


def les_portefolje(sti=STANDARD_FIL):
    """Leser og validerer portefolje.json, og returnerer listen med beholdninger."""
    if not os.path.exists(sti):
        raise PortefoljeFeil(
            f"Fant ikke porteføljefilen '{sti}'. "
            "Kopier portefolje.eksempel.json til portefolje.json og fyll inn dine tall."
        )

    try:
        with open(sti, encoding="utf-8") as fil:
            innhold = json.load(fil)
    except json.JSONDecodeError as e:
        raise PortefoljeFeil(f"Klarte ikke å lese '{sti}' som JSON: {e}") from e

    beholdninger = innhold.get("beholdninger") if isinstance(innhold, dict) else innhold
    if not isinstance(beholdninger, list):
        raise PortefoljeFeil("Porteføljefilen må inneholde en liste under nøkkelen 'beholdninger'.")

    validerte = []
    for nummer, rad in enumerate(beholdninger, start=1):
        if not isinstance(rad, dict):
            raise PortefoljeFeil(f"Beholdning nummer {nummer} er ikke et objekt.")

        symbol = str(rad.get("symbol", "")).strip()
        if not symbol:
            raise PortefoljeFeil(f"Beholdning nummer {nummer} mangler 'symbol'.")

        kilde = str(rad.get("kilde", "")).strip().lower()
        if kilde not in KILDER:
            raise PortefoljeFeil(
                f"'{symbol}' har ukjent kilde '{kilde}'. Bruk 'firi' for krypto eller 'yahoo' for aksjer og fond."
            )

        try:
            antall = float(rad.get("antall", 0) or 0)
            snittpris = float(rad.get("snittpris", 0) or 0)
        except (TypeError, ValueError) as e:
            raise PortefoljeFeil(f"'{symbol}' har ugyldig tall i 'antall' eller 'snittpris': {e}") from e

        if antall < 0:
            raise PortefoljeFeil(f"'{symbol}' har negativt antall.")

        validerte.append(
            {
                "symbol": symbol.upper() if kilde == "firi" else symbol,
                "navn": str(rad.get("navn") or symbol),
                "type": str(rad.get("type") or ("Krypto" if kilde == "firi" else "Aksjer og fond")),
                "kilde": kilde,
                "antall": antall,
                "snittpris": snittpris,
                # Firi handler alt i NOK; Yahoo-instrumenter kan handles i annen valuta
                "valuta": str(rad.get("valuta") or ("NOK" if kilde == "firi" else "")).upper(),
            }
        )

    if not validerte:
        raise PortefoljeFeil("Porteføljefilen er tom — legg inn minst én beholdning.")

    return validerte


def _hent_kurser(beholdninger):
    """Henter markedskurser for alle beholdningene, gruppert etter kilde."""
    krypto_symboler = {b["symbol"] for b in beholdninger if b["kilde"] == "firi"}
    yahoo_tickere = [b["symbol"] for b in beholdninger if b["kilde"] == "yahoo"]

    kryptoer = markeder.hent_firi_kryptoer(krypto_symboler) if krypto_symboler else {}
    aksjer = markeder.hent_yahoo_kurser(yahoo_tickere) if yahoo_tickere else {}
    return kryptoer, aksjer


def beregn_portefolje(beholdninger):
    """Priser hele porteføljen og regner ut verdi, gevinst og fordeling.

    Returnerer et oppslagsverk klart for JSON-serialisering til dashbordet.
    """
    kryptoer, aksjer = _hent_kurser(beholdninger)

    # Finn hvilke valutaer vi trenger vekslingskurs for
    valutaer = set()
    for beholdning in beholdninger:
        if beholdning["kilde"] == "firi":
            continue
        kurs = aksjer.get(beholdning["symbol"], {})
        valutaer.add(beholdning["valuta"] or kurs.get("valuta") or "NOK")
    valutakurser = markeder.hent_valutakurser(valutaer) if valutaer else {"NOK": 1.0}

    posisjoner = []
    advarsler = []
    for beholdning in beholdninger:
        posisjon = dict(beholdning)
        rådata = (
            kryptoer.get(beholdning["symbol"])
            if beholdning["kilde"] == "firi"
            else aksjer.get(beholdning["symbol"])
        )

        if not rådata:
            advarsler.append(f"Fant ingen kurs for {beholdning['symbol']} — den er utelatt fra totalen.")
            posisjon.update(
                {
                    "pris": None,
                    "valuta": beholdning["valuta"] or "NOK",
                    "valutakurs": None,
                    "verdi_nok": None,
                    "kostpris_nok": None,
                    "gevinst_nok": None,
                    "gevinst_prosent": None,
                    "endring24h": None,
                    "endring24h_nok": None,
                    "andel_prosent": None,
                    "mangler_kurs": True,
                }
            )
            posisjoner.append(posisjon)
            continue

        valuta = beholdning["valuta"] or rådata.get("valuta") or "NOK"
        valutakurs = valutakurser.get(valuta)
        if not valutakurs:
            advarsler.append(f"Fant ingen vekslingskurs for {valuta} — bruker 1,00 mot NOK for {beholdning['symbol']}.")
            valutakurs = 1.0

        pris = float(rådata["pris"])
        endring24h = float(rådata.get("endring24h") or 0.0)
        verdi_nok = pris * beholdning["antall"] * valutakurs
        kostpris_nok = beholdning["snittpris"] * beholdning["antall"] * valutakurs
        gevinst_nok = verdi_nok - kostpris_nok

        # Kronebeløpet av siste døgns bevegelse, regnet fra gårsdagens verdi
        if endring24h and endring24h > -100:
            verdi_i_gar = verdi_nok / (1 + endring24h / 100)
            endring24h_nok = verdi_nok - verdi_i_gar
        else:
            endring24h_nok = 0.0

        posisjon.update(
            {
                "pris": pris,
                "valuta": valuta,
                "valutakurs": valutakurs,
                "verdi_nok": verdi_nok,
                "kostpris_nok": kostpris_nok,
                "gevinst_nok": gevinst_nok,
                "gevinst_prosent": (gevinst_nok / kostpris_nok * 100) if kostpris_nok else None,
                "endring24h": endring24h,
                "endring24h_nok": endring24h_nok,
                "andel_prosent": None,  # settes når totalen er kjent
                "mangler_kurs": False,
            }
        )
        posisjoner.append(posisjon)

    prisede = [p for p in posisjoner if not p["mangler_kurs"]]
    total_verdi = sum(p["verdi_nok"] for p in prisede)
    total_kostpris = sum(p["kostpris_nok"] for p in prisede)
    total_endring24h = sum(p["endring24h_nok"] for p in prisede)

    for posisjon in prisede:
        posisjon["andel_prosent"] = (posisjon["verdi_nok"] / total_verdi * 100) if total_verdi else 0.0

    posisjoner.sort(key=lambda p: (p["verdi_nok"] is None, -(p["verdi_nok"] or 0)))

    # Delsummer per type, til gruppene i tabellen
    grupper = {}
    for posisjon in prisede:
        gruppe = grupper.setdefault(posisjon["type"], {"type": posisjon["type"], "verdi_nok": 0.0, "kostpris_nok": 0.0})
        gruppe["verdi_nok"] += posisjon["verdi_nok"]
        gruppe["kostpris_nok"] += posisjon["kostpris_nok"]
    for gruppe in grupper.values():
        gruppe["gevinst_nok"] = gruppe["verdi_nok"] - gruppe["kostpris_nok"]
        gruppe["andel_prosent"] = (gruppe["verdi_nok"] / total_verdi * 100) if total_verdi else 0.0

    verdi_i_gar = total_verdi - total_endring24h

    return {
        "oppdatert": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "posisjoner": posisjoner,
        "grupper": sorted(grupper.values(), key=lambda g: -g["verdi_nok"]),
        "valutakurser": valutakurser,
        "advarsler": advarsler,
        "totaler": {
            "verdi_nok": total_verdi,
            "kostpris_nok": total_kostpris,
            "gevinst_nok": total_verdi - total_kostpris,
            "gevinst_prosent": ((total_verdi - total_kostpris) / total_kostpris * 100) if total_kostpris else None,
            "endring24h_nok": total_endring24h,
            "endring24h_prosent": (total_endring24h / verdi_i_gar * 100) if verdi_i_gar else None,
            "antall_posisjoner": len(prisede),
        },
    }


def hent_oversikt(sti=STANDARD_FIL):
    """Leser porteføljefilen og returnerer ferdig beregnet oversikt."""
    return beregn_portefolje(les_portefolje(sti))


if __name__ == "__main__":
    print(json.dumps(hent_oversikt(), ensure_ascii=False, indent=2))
