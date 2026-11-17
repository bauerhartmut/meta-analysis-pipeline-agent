#!/usr/bin/env python3
"""Prueft, ob die 30 Goldstandard-Volltexte frei zugaenglich sind.

Kein Modellaufruf. Je Dokument wird die Kennung aus dem Volltextkopf gelesen
(DOI, PMID, PMCID) und bei Europe PMC sowie als Rueckfall bei Crossref
abgefragt: offener Zugang, Lizenz, Volltext-Links.

Ergebnis ist das Lizenzregister fuer die Weitergabe-Entscheidung:
``data/golden_effects/studienzugang_20261117.json`` plus eine Markdown-Tabelle
in ``docs/internal/studienzugang_20261117.md``.

Ein fehlender Treffer ist ein Befund, kein Fehler: er heisst, dass die
Kennung nicht aufgeloest werden konnte oder das Werk nicht offen vorliegt.

Aufruf::

    .venv/bin/python scripts/pruefe_studien_zugang.py
    .venv/bin/python scripts/pruefe_studien_zugang.py --nur-bekannte   # kein Netz fuer Rest
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "golden_effects" / "blind_b_20261110" / "manifest.json"
ZIEL_JSON = ROOT / "data" / "golden_effects" / "studienzugang_20261117.json"
ZIEL_MD = ROOT / "docs" / "internal" / "studienzugang_20261117.md"

UA = "AIResearch-Goldstandard-Lizenzcheck/1.0 (Forschungsprojekt, Kontakt lokal)"
DOI_RE = re.compile(r"10\.[0-9]{4,9}/[^\s\"<>]+")
PMID_RE = re.compile(r"PMID:?\s*([0-9]{6,9})")
PMC_RE = re.compile(r"(PMC[0-9]{6,9})")


def hole(url: str, versuche: int = 3) -> dict | None:
    """GET mit kleinem Backoff; None bei dauerhaftem Fehlschlag."""
    for i in range(versuche):
        try:
            anfrage = urllib.request.Request(url, headers={"User-Agent": UA,
                                                           "Accept": "application/json"})
            with urllib.request.urlopen(anfrage, timeout=25) as antwort:
                return json.loads(antwort.read().decode("utf-8", errors="replace"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            if i + 1 < versuche:
                time.sleep(1.5 * (i + 1))
    return None


def kennungen(text: str) -> dict:
    kopf = text[:3000]
    doi = DOI_RE.search(kopf) or DOI_RE.search(text)
    pmid = PMID_RE.search(text[:6000])
    pmc = PMC_RE.search(text[:6000])
    roh = doi.group(0).rstrip(".,);]") if doi else ""
    # Bei Beilagen steht die Supplement-DOI im Text (z. B. .../s1). Der Artikel
    # selbst ist ueber die Basis-DOI zu finden; beides wird abgefragt.
    basis = re.sub(r"/s[0-9]{1,2}$", "", roh)
    return {
        "doi": roh,
        "doi_basis": "" if basis == roh else basis,
        "pmid": (pmid.group(1) if pmid else ""),
        "pmcid": (pmc.group(1) if pmc else ""),
    }


def _epmc_frage(frage: str) -> dict | None:
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
           + urllib.parse.urlencode({"query": frage, "format": "json",
                                     "resultType": "core", "pageSize": 1}))
    return hole(url)


def europe_pmc(kennung: dict) -> dict | None:
    fragen = []
    if kennung["doi"]:
        fragen.append(f'DOI:"{kennung["doi"]}"')
    if kennung.get("doi_basis"):
        fragen.append(f'DOI:"{kennung["doi_basis"]}"')
    if kennung["pmid"]:
        fragen.append(f"EXT_ID:{kennung['pmid']}")
    if kennung["pmcid"]:
        fragen.append(f"PMCID:{kennung['pmcid']}")
    if not fragen:
        return None
    daten = None
    for frage in fragen:
        daten = _epmc_frage(frage)
        treffer = ((daten or {}).get("resultList") or {}).get("result") or []
        if treffer:
            break
        time.sleep(0.3)
    treffer = ((daten or {}).get("resultList") or {}).get("result") or []
    if not treffer:
        return None
    r = treffer[0]
    quellen = [
        {"site": q.get("site"), "availability": q.get("availability"),
         "license": q.get("license"), "url": q.get("url")}
        for q in ((r.get("fullTextUrlList") or {}).get("fullTextUrl") or [])
    ]
    return {
        "quelle": "europepmc",
        "pmid": r.get("pmid") or "",
        "pmcid": r.get("pmcid") or "",
        "doi": r.get("doi") or "",
        "journal": r.get("journalTitle") or r.get("bookOrReportDetails", {}).get("publisher") or "",
        "year": r.get("pubYear") or "",
        "is_open_access": r.get("isOpenAccess") or "",
        "in_epmc": r.get("inEPMC") or "",
        "in_pmc": r.get("inPMC") or "",
        "license": r.get("license") or "",
        "links": quellen,
    }


def crossref(doi: str) -> dict | None:
    if not doi:
        return None
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    daten = hole(url)
    nachricht = (daten or {}).get("message")
    if not nachricht:
        return None
    lizenzen = [l.get("URL") for l in (nachricht.get("license") or []) if l.get("URL")]
    return {
        "quelle": "crossref",
        "titel": ((nachricht.get("title") or [""])[0] or "")[:160],
        "verlag": nachricht.get("publisher") or "",
        "lizenzen": lizenzen,
        "link": ((nachricht.get("link") or [{}])[0].get("URL") or ""),
    }


def einschaetzung(eintrag: dict) -> str:
    """Kurzurteil fuer die Weitergabe, nur aus den Befunden abgeleitet."""
    epmc = eintrag.get("europepmc") or {}
    if epmc.get("is_open_access") == "Y":
        lizenz = (epmc.get("license") or "").lower()
        if lizenz.startswith(("cc by", "cc-by", "cc0", "cc by-nc")):
            return "offen, Lizenz genannt"
        return "offen, Lizenz pruefen"
    if epmc.get("in_pmc") == "Y":
        return "in PMC, aber nicht als OA gekennzeichnet"
    if (eintrag.get("crossref") or {}).get("lizenzen"):
        return "nur Verlagslizenz, offener Zugang unklar"
    return "kein offener Nachweis"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nur-bekannte", action="store_true",
                        help="Dokumente ohne Kennung nicht abfragen")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    docs = manifest.get("documents") or []
    ergebnisse = []
    for nummer, doc in enumerate(docs, start=1):
        pfad = ROOT / doc["fulltext"]
        text = pfad.read_text(encoding="utf-8", errors="replace")
        kennung = kennungen(text)
        eintrag = {
            "document_id": doc["document_id"],
            "titel": doc.get("title") or "",
            "kennung": kennung,
            "europepmc": None,
            "crossref": None,
        }
        if kennung["doi"] or kennung["pmid"] or kennung["pmcid"]:
            eintrag["europepmc"] = europe_pmc(kennung)
            time.sleep(0.3)
        elif not args.nur_bekannte and doc.get("title"):
            # Ohne Kennung im Text hilft nur die Titelsuche; der Treffer wird
            # als solcher gekennzeichnet, weil er nicht aus dem Text stammt.
            titel = re.sub(r'[":()\[\]]', " ", doc["title"])[:120].strip()
            daten = _epmc_frage(f'TITLE:"{titel}"')
            treffer = ((daten or {}).get("resultList") or {}).get("result") or []
            r = treffer[0] if treffer else None
            if r:
                eintrag["europepmc"] = {
                    "quelle": "europepmc-titelsuche",
                    "pmid": r.get("pmid") or "", "pmcid": r.get("pmcid") or "",
                    "doi": r.get("doi") or "",
                    "journal": r.get("journalTitle") or "",
                    "year": r.get("pubYear") or "",
                    "is_open_access": r.get("isOpenAccess") or "",
                    "in_pmc": r.get("inPMC") or "", "in_epmc": r.get("inEPMC") or "",
                    "license": r.get("license") or "",
                    "links": [{"site": q.get("site"), "availability": q.get("availability"),
                               "license": q.get("license"), "url": q.get("url")}
                              for q in ((r.get("fullTextUrlList") or {}).get("fullTextUrl") or [])],
                }
            time.sleep(0.3)
        if not (eintrag["europepmc"] or {}).get("is_open_access") == "Y" and kennung["doi"]:
            eintrag["crossref"] = crossref(kennung["doi"])
            time.sleep(0.3)
        eintrag["urteil"] = einschaetzung(eintrag)
        ergebnisse.append(eintrag)
        print(f"[{nummer:2d}/30] {doc['document_id'][:10]} "
              f"{kennung['doi'][:34] or '-':36s} {eintrag['urteil']}", flush=True)

    datei = {
        "stand": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "quelle": "Europe PMC REST (resultType=core), Rueckfall Crossref works",
        "n_dokumente": len(ergebnisse),
        "dokumente": ergebnisse,
    }
    ZIEL_JSON.parent.mkdir(parents=True, exist_ok=True)
    ZIEL_JSON.write_text(json.dumps(datei, indent=1, ensure_ascii=False) + "\n",
                         encoding="utf-8")

    zeilen = [
        "# Zugang und Lizenz der 30 Goldstandard-Volltexte (2026-11-17)",
        "",
        "Kein Modellaufruf. Kennungen aus dem Volltextkopf, Abfrage bei Europe PMC",
        "(REST, `resultType=core`) und als Rueckfall bei Crossref. Ein fehlender",
        "Treffer ist ein Befund, kein Fehler.",
        "",
        "| Dokument | DOI | Europe PMC | Lizenz | Urteil |",
        "|---|---|---|---|---|",
    ]
    for e in ergebnisse:
        epmc = e.get("europepmc") or {}
        zeilen.append(
            f"| `{e['document_id'][:10]}` | {e['kennung']['doi'] or '-'} | "
            f"{(epmc.get('is_open_access') or '-')} | {(epmc.get('license') or '-')} | "
            f"{e['urteil']} |"
        )
    offen = sum(1 for e in ergebnisse if e["urteil"].startswith("offen"))
    ohne = [e for e in ergebnisse if not any(e["kennung"].values())]
    zeilen += [
        "",
        f"**Offen zugaenglich: {offen} von {len(ergebnisse)}.** "
        f"Ohne Kennung: {len(ohne)}"
        + ("" if not ohne else " (" + ", ".join(f"`{e['document_id'][:10]}`" for e in ohne) + ")"),
        "",
    ]
    ZIEL_MD.parent.mkdir(parents=True, exist_ok=True)
    ZIEL_MD.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    print(f"\nRegister: {ZIEL_JSON.relative_to(ROOT)} | Bericht: {ZIEL_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
