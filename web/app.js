/* PurrFolio – dashbordlogikk.
   Henter beregnet portefølje fra /api/portefolje og tegner den opp. */

const OPPDATERINGSINTERVALL = 30000; // millisekunder mellom hver henting
const ANTALL_SERIEFARGER = 8;        // kategoripaletten har åtte faste plasser

const kroneformat = new Intl.NumberFormat("nb-NO", {
  style: "currency",
  currency: "NOK",
  maximumFractionDigits: 0,
});

const kroneformatPresis = new Intl.NumberFormat("nb-NO", {
  style: "currency",
  currency: "NOK",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const klokkeformat = new Intl.DateTimeFormat("nb-NO", { hour: "2-digit", minute: "2-digit" });

let sisteData = null;
let henterNa = false;

/* Formatering ---------------------------------------------------------- */

function kroner(verdi) {
  if (verdi === null || verdi === undefined) return "–";
  // Små kurser (typisk XRP eller ADA) trenger øre for å si noe
  return Math.abs(verdi) < 100 ? kroneformatPresis.format(verdi) : kroneformat.format(verdi);
}

function signerteKroner(verdi) {
  if (verdi === null || verdi === undefined) return "–";
  const fortegn = verdi > 0 ? "+" : verdi < 0 ? "−" : "";
  return fortegn + kroner(Math.abs(verdi));
}

function prosent(verdi, desimaler = 2) {
  if (verdi === null || verdi === undefined) return "–";
  const fortegn = verdi > 0 ? "+" : verdi < 0 ? "−" : "";
  return `${fortegn}${Math.abs(verdi).toFixed(desimaler).replace(".", ",")} %`;
}

function antallFormat(verdi) {
  if (verdi === null || verdi === undefined) return "–";
  const desimaler = Math.abs(verdi) >= 1000 ? 0 : Math.abs(verdi) >= 1 ? 4 : 8;
  return verdi.toLocaleString("nb-NO", { maximumFractionDigits: desimaler });
}

/* Retningen får både farge og en pil, slik at fargen aldri bærer meningen alene */
function retningsklasse(verdi) {
  if (!verdi) return "";
  return verdi > 0 ? "opp" : "ned";
}

function settRetning(element, verdi) {
  const klasse = retningsklasse(verdi);
  if (klasse) element.classList.add(klasse);
  return element;
}

function pil(verdi) {
  if (!verdi) return "";
  return verdi > 0 ? "▲ " : "▼ ";
}

function seriefarge(nummer) {
  return `var(--serie-${(nummer % ANTALL_SERIEFARGER) + 1})`;
}

function settTekst(id, tekst, klasse = "") {
  const element = document.getElementById(id);
  element.textContent = tekst;
  element.className = element.className.replace(/\b(opp|ned)\b/g, "").trim();
  if (klasse) element.classList.add(klasse);
}

/* Henting -------------------------------------------------------------- */

async function hentPortefolje() {
  if (henterNa) return;
  henterNa = true;

  const knapp = document.getElementById("oppdater-knapp");
  const puls = document.getElementById("puls");
  knapp.disabled = true;
  puls.className = "puls henter";
  if (!sisteData) document.getElementById("status-tekst").textContent = "Henter kurser …";

  try {
    const svar = await fetch("/api/portefolje", { cache: "no-store" });
    const data = await svar.json();

    if (!svar.ok) throw new Error(data.feil || `Serveren svarte ${svar.status}.`);

    sisteData = data;
    visFeil(null);
    tegnDashbord(data);
    puls.className = "puls";
  } catch (feil) {
    // Beholder forrige tallgrunnlag på skjermen — en tapt henting skal ikke tømme siden
    visFeil(feil.message || String(feil));
    document.getElementById("puls").className = "puls feilet";
    document.getElementById("status-tekst").textContent = "Kursene er ikke oppdatert";
  } finally {
    henterNa = false;
    knapp.disabled = false;
  }
}

function visFeil(melding) {
  const boks = document.getElementById("feilmelding");
  boks.hidden = !melding;
  boks.textContent = melding || "";
}

function visAdvarsler(advarsler) {
  const boks = document.getElementById("advarsler");
  if (!advarsler || !advarsler.length) {
    boks.hidden = true;
    boks.innerHTML = "";
    return;
  }
  boks.hidden = false;
  boks.innerHTML = "<strong>Merk</strong><ul></ul>";
  const liste = boks.querySelector("ul");
  for (const advarsel of advarsler) {
    const punkt = document.createElement("li");
    punkt.textContent = advarsel;
    liste.appendChild(punkt);
  }
}

/* Opptegning ----------------------------------------------------------- */

function tegnDashbord(data) {
  const totaler = data.totaler;

  settTekst("total-verdi", kroneformat.format(totaler.verdi_nok));
  settTekst(
    "total-gevinst",
    `${pil(totaler.gevinst_nok)}${signerteKroner(totaler.gevinst_nok)} (${prosent(totaler.gevinst_prosent)}) siden kjøp`,
    retningsklasse(totaler.gevinst_nok)
  );

  settTekst("total-kostpris", kroneformat.format(totaler.kostpris_nok));
  settTekst("antall-posisjoner", `${totaler.antall_posisjoner} poster med kurs`);

  settTekst(
    "endring-doegn",
    `${pil(totaler.endring24h_nok)}${signerteKroner(totaler.endring24h_nok)}`,
    retningsklasse(totaler.endring24h_nok)
  );
  settTekst("endring-doegn-prosent", `${prosent(totaler.endring24h_prosent)} av porteføljen`);

  settTekst("gevinst-kroner", signerteKroner(totaler.gevinst_nok), retningsklasse(totaler.gevinst_nok));
  settTekst("gevinst-prosent", `${prosent(totaler.gevinst_prosent)} avkastning`);

  const storste = data.posisjoner.find((post) => !post.mangler_kurs);
  settTekst("storste-post", storste ? storste.navn : "–");
  settTekst("storste-andel", storste ? `${prosent(storste.andel_prosent, 1)} av totalen`.replace("+", "") : "–");

  tegnFordeling(data.posisjoner, totaler.verdi_nok);
  tegnTabell(data);
  visAdvarsler(data.advarsler);

  const tidspunkt = new Date(data.oppdatert);
  document.getElementById("status-tekst").textContent = `Oppdatert ${klokkeformat.format(tidspunkt)}`;

  const valutalinjer = Object.entries(data.valutakurser)
    .filter(([valuta]) => valuta !== "NOK")
    .map(([valuta, kurs]) => `1 ${valuta} = ${kurs.toFixed(2).replace(".", ",")} NOK`);
  document.getElementById("valutanotat").textContent = valutalinjer.length
    ? `Vekslingskurser: ${valutalinjer.join(" · ")}`
    : "";
}

/* Del-av-helhet: én liggende stabel, de sju største postene pluss «Annet» */
function fordelingsdeler(posisjoner) {
  const prisede = posisjoner.filter((post) => !post.mangler_kurs && post.verdi_nok > 0);
  const storste = prisede.slice(0, ANTALL_SERIEFARGER - 1);
  const resten = prisede.slice(ANTALL_SERIEFARGER - 1);

  const deler = storste.map((post, nummer) => ({
    navn: post.navn,
    verdi: post.verdi_nok,
    andel: post.andel_prosent,
    farge: seriefarge(nummer),
  }));

  if (resten.length) {
    deler.push({
      navn: `Annet (${resten.length} poster)`,
      verdi: resten.reduce((sum, post) => sum + post.verdi_nok, 0),
      andel: resten.reduce((sum, post) => sum + post.andel_prosent, 0),
      farge: seriefarge(ANTALL_SERIEFARGER - 1),
    });
  }

  return deler;
}

function tegnFordeling(posisjoner, totalVerdi) {
  const stabel = document.getElementById("fordeling-stabel");
  const forklaring = document.getElementById("fordeling-tegnforklaring");
  stabel.innerHTML = "";
  forklaring.innerHTML = "";

  const deler = fordelingsdeler(posisjoner);
  if (!deler.length || !totalVerdi) {
    forklaring.innerHTML = "<li>Ingen prisede poster ennå.</li>";
    return;
  }

  for (const del of deler) {
    const segment = document.createElement("div");
    segment.className = "segment";
    segment.style.flex = `${Math.max(del.verdi, 0)} 0 auto`;
    segment.style.background = del.farge;
    knyttVerktoytips(segment, del);
    stabel.appendChild(segment);

    const punkt = document.createElement("li");
    const prikk = document.createElement("span");
    prikk.className = "prikk";
    prikk.style.background = del.farge;
    const navn = document.createElement("span");
    navn.textContent = del.navn;
    const andel = document.createElement("span");
    andel.className = "andel";
    andel.textContent = `${del.andel.toFixed(1).replace(".", ",")} %`;
    punkt.append(prikk, navn, andel);
    knyttVerktoytips(punkt, del);
    forklaring.appendChild(punkt);
  }
}

function knyttVerktoytips(element, del) {
  const tips = document.getElementById("verktoytips");

  const vis = (hendelse) => {
    tips.innerHTML = "";
    const navn = document.createElement("div");
    navn.className = "tips-navn";
    navn.textContent = del.navn;
    const verdi = document.createElement("div");
    verdi.className = "tips-linje";
    verdi.textContent = `${kroneformat.format(del.verdi)} · ${del.andel.toFixed(1).replace(".", ",")} % av porteføljen`;
    tips.append(navn, verdi);
    tips.hidden = false;
    flyttVerktoytips(hendelse);
  };

  const flyttVerktoytips = (hendelse) => {
    const bredde = tips.offsetWidth;
    const venstre = Math.min(hendelse.clientX + 12, window.innerWidth - bredde - 12);
    tips.style.left = `${Math.max(12, venstre)}px`;
    tips.style.top = `${hendelse.clientY + 16}px`;
  };

  element.addEventListener("pointerenter", vis);
  element.addEventListener("pointermove", flyttVerktoytips);
  element.addEventListener("pointerleave", () => {
    tips.hidden = true;
  });
}

function tegnTabell(data) {
  const kropp = document.getElementById("beholdning-rader");
  kropp.innerHTML = "";

  if (!data.posisjoner.length) {
    kropp.innerHTML = '<tr><td colspan="8" class="tomt">Ingen beholdninger i portefolje.json.</td></tr>';
    return;
  }

  // Grupperer etter type, med delsum per gruppe
  const typer = data.grupper.map((gruppe) => gruppe.type);
  for (const type of new Set(data.posisjoner.map((post) => post.type))) {
    if (!typer.includes(type)) typer.push(type);
  }
  for (const type of typer) {
    const gruppe = data.grupper.find((g) => g.type === type);
    kropp.appendChild(lagGrupperad(type, gruppe));
    for (const post of data.posisjoner.filter((p) => p.type === type)) {
      kropp.appendChild(lagPostrad(post));
    }
  }

  kropp.appendChild(lagSumrad(data.totaler));
}

function lagCelle(innhold, klasse = "") {
  const celle = document.createElement("td");
  if (klasse) celle.className = klasse;
  if (innhold instanceof Node) celle.appendChild(innhold);
  else celle.textContent = innhold;
  return celle;
}

function lagGrupperad(type, gruppe) {
  const rad = document.createElement("tr");
  rad.className = "gruppe-rad";
  rad.appendChild(lagCelle(type));
  rad.appendChild(lagCelle("", "tall"));
  rad.appendChild(lagCelle("", "tall"));
  rad.appendChild(lagCelle("", "tall"));
  rad.appendChild(lagCelle(gruppe ? kroneformat.format(gruppe.verdi_nok) : "", "tall"));
  rad.appendChild(lagCelle(gruppe ? `${gruppe.andel_prosent.toFixed(1).replace(".", ",")} %` : "", "tall"));
  rad.appendChild(lagCelle("", "tall"));

  const gevinst = lagCelle(gruppe ? signerteKroner(gruppe.gevinst_nok) : "", "tall");
  if (gruppe) settRetning(gevinst, gruppe.gevinst_nok);
  rad.appendChild(gevinst);
  return rad;
}

function lagPostrad(post) {
  const rad = document.createElement("tr");

  const navn = document.createElement("span");
  navn.className = "post";
  const tittel = document.createElement("span");
  tittel.textContent = post.navn;
  const symbol = document.createElement("span");
  symbol.className = "symbol";
  symbol.textContent = post.symbol;
  navn.append(tittel, symbol);
  rad.appendChild(lagCelle(navn));

  rad.appendChild(lagCelle(antallFormat(post.antall), "tall"));

  if (post.mangler_kurs) {
    rad.appendChild(lagCelle(`${antallFormat(post.snittpris)} ${post.valuta}`, "tall"));
    const melding = lagCelle("ingen kurs", "tall mangler");
    melding.colSpan = 5;
    rad.appendChild(melding);
    return rad;
  }

  const valutasuffiks = post.valuta === "NOK" ? "" : ` ${post.valuta}`;
  rad.appendChild(lagCelle(`${antallFormat(post.snittpris)}${valutasuffiks}`, "tall"));
  rad.appendChild(lagCelle(`${antallFormat(post.pris)}${valutasuffiks}`, "tall"));
  rad.appendChild(lagCelle(kroneformat.format(post.verdi_nok), "tall"));
  rad.appendChild(lagCelle(`${post.andel_prosent.toFixed(1).replace(".", ",")} %`, "tall"));

  const doegn = lagCelle(`${pil(post.endring24h)}${prosent(post.endring24h)}`, "tall");
  settRetning(doegn, post.endring24h);
  rad.appendChild(doegn);

  const gevinst = document.createElement("span");
  gevinst.textContent = `${signerteKroner(post.gevinst_nok)} (${prosent(post.gevinst_prosent, 1)})`;
  const gevinstcelle = lagCelle(gevinst, "tall");
  settRetning(gevinstcelle, post.gevinst_nok);
  rad.appendChild(gevinstcelle);

  return rad;
}

function lagSumrad(totaler) {
  const rad = document.createElement("tr");
  rad.className = "sum-rad";
  rad.appendChild(lagCelle("Totalt"));
  rad.appendChild(lagCelle("", "tall"));
  rad.appendChild(lagCelle("", "tall"));
  rad.appendChild(lagCelle("", "tall"));
  rad.appendChild(lagCelle(kroneformat.format(totaler.verdi_nok), "tall"));
  rad.appendChild(lagCelle("100 %", "tall"));

  const doegn = lagCelle(`${pil(totaler.endring24h_nok)}${prosent(totaler.endring24h_prosent)}`, "tall");
  settRetning(doegn, totaler.endring24h_nok);
  rad.appendChild(doegn);

  const gevinst = lagCelle(
    `${signerteKroner(totaler.gevinst_nok)} (${prosent(totaler.gevinst_prosent, 1)})`,
    "tall"
  );
  settRetning(gevinst, totaler.gevinst_nok);
  rad.appendChild(gevinst);
  return rad;
}

/* Oppstart ------------------------------------------------------------- */

document.getElementById("oppdater-knapp").addEventListener("click", hentPortefolje);

// Henter ikke kurser mens fanen ligger i bakgrunnen, men tar en runde straks den er synlig igjen
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) hentPortefolje();
});

setInterval(() => {
  if (!document.hidden) hentPortefolje();
}, OPPDATERINGSINTERVALL);

hentPortefolje();
