"""Lokalt porteføljedashboard for PurrFolio.

Starter en liten webserver på maskinen din som viser beholdningene dine med
live kurser fra Firi og Yahoo Finance:

    python dashbord.py

Serveren lytter bare på 127.0.0.1, så tallene dine forlater aldri maskinen.
"""

import argparse
import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import portefolje

WEB_MAPPE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

# Filene dashbordet får lov til å servere, med tilhørende innholdstype
STATISKE_FILER = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/stil.css": ("stil.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


class Kursbuffer:
    """Mellomlagrer beregnet portefølje slik at nettleseren ikke spammer API-ene.

    Bufferen tømmes også når portefolje.json endres, så redigeringer slår
    gjennom med én gang uten omstart av serveren.
    """

    def __init__(self, sti, levetid_sekunder):
        self.sti = sti
        self.levetid = levetid_sekunder
        self._lås = threading.Lock()
        self._data = None
        self._hentet = 0.0
        self._filstempel = None

    def _filendret(self):
        try:
            return os.path.getmtime(self.sti)
        except OSError:
            return None

    def hent(self):
        import time

        with self._lås:
            filstempel = self._filendret()
            fersk = (
                self._data is not None
                and (time.monotonic() - self._hentet) < self.levetid
                and filstempel == self._filstempel
            )
            if not fersk:
                self._data = portefolje.hent_oversikt(self.sti)
                self._hentet = time.monotonic()
                self._filstempel = filstempel
            return self._data


class Dashbordbehandler(BaseHTTPRequestHandler):
    server_version = "PurrFolio"
    buffer = None

    def do_GET(self):
        rute = self.path.split("?")[0]

        if rute == "/api/portefolje":
            self._send_api()
        elif rute in STATISKE_FILER:
            filnavn, innholdstype = STATISKE_FILER[rute]
            self._send_fil(filnavn, innholdstype)
        else:
            self._send_json(404, {"feil": "Ukjent adresse."})

    def _send_api(self):
        try:
            self._send_json(200, self.buffer.hent())
        except portefolje.PortefoljeFeil as e:
            self._send_json(400, {"feil": str(e)})
        except Exception as e:  # noe uventet i prishentingen
            self._send_json(500, {"feil": f"Klarte ikke å hente porteføljen: {e}"})

    def _send_fil(self, filnavn, innholdstype):
        try:
            with open(os.path.join(WEB_MAPPE, filnavn), "rb") as fil:
                innhold = fil.read()
        except OSError:
            self._send_json(500, {"feil": f"Fant ikke {filnavn} i web-mappen."})
            return

        self.send_response(200)
        self.send_header("Content-Type", innholdstype)
        self.send_header("Content-Length", str(len(innhold)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(innhold)

    def _send_json(self, status, data):
        kropp = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(kropp)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(kropp)

    def log_message(self, format, *args):
        """Demper standardloggen — én linje per forespørsel holder."""
        print(f"{self.command} {self.path}")


def start_dashbord(port=8000, sti=portefolje.STANDARD_FIL, levetid=30, apne_nettleser=True):
    Dashbordbehandler.buffer = Kursbuffer(sti, levetid)
    server = ThreadingHTTPServer(("127.0.0.1", port), Dashbordbehandler)
    adresse = f"http://127.0.0.1:{port}"

    print(f"🐱 PurrFolio-dashbordet kjører på {adresse}")
    print(f"   Portefølje: {sti}")
    print("   Avslutt med Ctrl+C")

    if apne_nettleser:
        threading.Timer(0.5, lambda: webbrowser.open(adresse)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAvslutter dashbordet.")
    finally:
        server.server_close()


if __name__ == "__main__":
    argumenter = argparse.ArgumentParser(description="Lokalt porteføljedashboard for PurrFolio")
    argumenter.add_argument("--port", type=int, default=8000, help="Port å lytte på (standard: 8000)")
    argumenter.add_argument("--fil", default=portefolje.STANDARD_FIL, help="Sti til porteføljefilen")
    argumenter.add_argument("--buffer", type=int, default=30, help="Sekunder kursene mellomlagres (standard: 30)")
    argumenter.add_argument("--ingen-nettleser", action="store_true", help="Ikke åpne nettleseren automatisk")
    valg = argumenter.parse_args()

    start_dashbord(
        port=valg.port,
        sti=valg.fil,
        levetid=valg.buffer,
        apne_nettleser=not valg.ingen_nettleser,
    )
