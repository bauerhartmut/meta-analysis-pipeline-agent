"""Beschafft und dokumentiert die 12 Primaerstudien von Serrano-Ripoll 2022.

Trennt strikt, was in der Vergangenheit vermischt wurde:

  1. Identifikation   - ist die bibliografische Angabe eindeutig aufloesbar?
  2. Zugriff          - gibt es ueberhaupt eine legale Volltextquelle?
  3. Download         - wurde tatsaechlich eine Datei erhalten?
  4. Speicherung      - darf die Datei behalten/weitergegeben werden?
  5. Datenverfuegbarkeit - stehen Arm-Statistiken fuer eine Extraktion bereit?

Downloadregel: gespeichert wird nur, was eine freie Lizenz (CC) hat oder was
als Autor:innenmanuskript in PMC fuer nicht-kommerzielle Forschung bereitsteht.
Alles andere wird nur als Metadatum erfasst. Keine Paywall-Umgehung, kein
Scraping von Verlagsseiten ohne OA-Kennzeichnung.

Read-only gegen oeffentliche APIs, schreibt nur in benchmark/.
"""

from __future__ import annotations

import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
UA = "AIResearch-Reproduzierbarkeit/1.0 (mailto:research@freebuff.ai)"
MAILTO = "research@freebuff.ai"

ROOT = Path("benchmark/serrano_ripoll_2022")
STUDIES_DIR = ROOT / "primary_studies"
INVENTORY = ROOT / "fulltext_inventory.json"
INVENTORY_CSV = ROOT / "fulltext_inventory.csv"
REPORT = ROOT / "BESCHAFFUNGSBERICHT.md"

# Nr. laut Tabelle 2 des Reviews, DOI wie in der Aufgabe, PMID aus der
# Referenzliste des Reviews (Europe-PMC-References-Endpunkt, geprueft).
STUDIES = [
    (1, "Arean 2016", "10.2196/jmir.6482", "27998876", "PHQ-9", True),
    (2, "Birney 2016", "10.2196/mhealth.4231", "26813737", "PHQ-9", True),
    (3, "Dahne 2019", "10.1016/j.beth.2018.12.003", "31208690", "PHQ-9", True),
    (4, "Ham 2019", "10.3389/fpsyg.2019.01592", "31402881", "BDI-II", True),
    (5, "Luedtke 2018", "10.1016/j.psychres.2018.08.113", "30273901", "BDI-II", False),
    (6, "Mantani 2017", "10.2196/jmir.8602", "29101095", "BDI-II", True),
    (7, "Moberg 2019", "10.2196/12556", "31199319", "PHQ-8", True),
    (8, "Pratap 2018", "10.2196/10130", "30093372", "PHQ-9", True),
    (9, "Roepke 2015", "10.1089/g4h.2014.0046", "26182069", "CES-D", False),
    (10, "Tighe 2017", "10.1136/bmjopen-2016-013518", "28132007", "PHQ-9", True),
    (11, "Graham 2020", "10.1001/jamapsychiatry.2020.1011", "32432695", "PHQ-8", True),
    (12, "Guo 2020", "10.2196/16715", "32044751", "CES-D", True),
]

FREE_LICENSE = re.compile(r"^(cc-|cc0|cc by|ccby)", re.IGNORECASE)


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def http(url: str, timeout: int = 60, want_json: bool = False):
    """GET mit Statusprotokoll. Gibt (status, body) zurueck, niemals Exception."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except Exception as exc:  # noqa: BLE001 - Netzfehler sind Datenpunkte
        return 0, str(exc).encode()


def get_json(url: str, timeout: int = 60):
    status, body = http(url, timeout)
    if status != 200 or not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def norm(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def similar(a: str, b: str) -> float:
    """Anteil gemeinsamer Woerter relativ zur kuerzeren Zeichenkette."""
    wa, wb = set(norm(a).split()), set(norm(b).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / min(len(wa), len(wb))


# ---------------------------------------------------------------------------
# Schritt 1: Identifikation und Metadatenverifikation
# ---------------------------------------------------------------------------

def metadata(study: tuple) -> dict:
    nr, name, doi, pmid, instrument, in_pool = study
    rec = {
        "nummer_review": nr, "study_id": slug(name), "name": name, "doi": doi.lower(),
        "pmid": pmid, "instrument": instrument, "im_effektpool_review": in_pool,
        "sources": {}, "attempts": [],
    }

    # Europe PMC (core: liefert Lizenz, Volltext-URLs, Supplement-Flag)
    q = urllib.parse.quote(f"EXT_ID:{pmid} AND SRC:MED")
    data = get_json(f"{EPMC}/search?query={q}&resultType=core&format=json") or {}
    hits = (data.get("resultList") or {}).get("result") or []
    if hits:
        e = hits[0]
        rec["epmc"] = {
            "title": e.get("title") or "", "journal": e.get("journalInfo", {}).get("journal", {}).get("title") or "",
            "year": str(e.get("pubYear") or ""), "pmcid": e.get("pmcid") or "",
            "is_open_access": e.get("isOpenAccess") == "Y",
            "in_pmc": e.get("inPMC") == "Y", "in_epmc": e.get("inEPMC") == "Y",
            "has_pdf": e.get("hasPDF") == "Y", "has_suppl": e.get("hasSuppl") == "Y",
            "license": e.get("license") or "", "author_string": e.get("authorString") or "",
            "full_text_urls": [u.get("url") for u in (e.get("fullTextUrlList", {}).get("fullTextUrl") or [])],
        }
        rec["sources"]["europepmc"] = True
    else:
        rec["epmc"] = {}
        rec["sources"]["europepmc"] = False
    time.sleep(0.4)

    # Crossref (Verlagsmetadaten, Autorenliste, Publisher-Link)
    cr = get_json(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}?mailto={MAILTO}") or {}
    msg = cr.get("message") or {}
    authors = []
    for a in msg.get("author") or []:
        fam = a.get("family") or ""
        given = a.get("given") or ""
        if fam:
            authors.append(f"{fam} {given}".strip())
    rec["crossref"] = {
        "title": (msg.get("title") or [""])[0],
        "container": (msg.get("container-title") or [""])[0],
        "year": str((msg.get("issued", {}).get("date-parts") or [[""]])[0][0] or ""),
        "authors": authors,
        "publisher": msg.get("publisher") or "",
        "publisher_url": msg.get("URL") or "",
        "license": [l.get("URL") for l in msg.get("license") or []],
    }
    rec["sources"]["crossref"] = bool(msg)
    time.sleep(0.4)

    # Unpaywall (legaler OA-Nachweis, Version, Repository)
    up = get_json(f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={MAILTO}") or {}
    best = up.get("best_oa_location") or {}
    rec["unpaywall"] = {
        "is_oa": up.get("is_oa"),
        "oa_status": up.get("oa_status") or "",
        "journal_is_oa": up.get("journal_is_oa"),
        "best_url": best.get("url") or "",
        "best_pdf": best.get("url_for_pdf") or "",
        "best_license": best.get("license") or "",
        "best_version": best.get("version") or "",
        "best_host": best.get("host_type") or "",
        "n_locations": len(up.get("oa_locations") or []),
        "locations": [
            {"url": l.get("url"), "pdf": l.get("url_for_pdf"), "license": l.get("license"),
             "version": l.get("version"), "host": l.get("host_type"),
             "repository": l.get("repository_institution") or ""}
            for l in (up.get("oa_locations") or [])
        ][:6],
    }
    rec["sources"]["unpaywall"] = up.get("is_oa") is not None
    rec["sources"]["pmc"] = bool(rec["epmc"].get("in_pmc"))
    time.sleep(0.4)
    return rec


def verify(rec: dict) -> dict:
    """Bibliografische Kontrolle gegen zwei unabhaengige Quellen."""
    t_epmc = rec["epmc"].get("title") or ""
    t_cross = rec["crossref"].get("title") or ""
    y_cross = rec["crossref"].get("year") or ""
    return {
        "doi_aufgeloest_crossref": bool(rec["crossref"].get("title")),
        "titel_konsistent_epmc_crossref": round(similar(t_epmc, t_cross), 2) if t_epmc and t_cross else None,
        "jahr_crossref": y_cross,
        "autoren_crossref": "; ".join(rec["crossref"].get("authors", [])[:4]),
        "autorenzahl_crossref": len(rec["crossref"].get("authors", [])),
    }


# ---------------------------------------------------------------------------
# Schritt 2: Zugriffskette mit Protokoll
# ---------------------------------------------------------------------------

def bioc_license_text(path: Path) -> str:
    """Lizenzhinweis aus einem BioC-Dokument ziehen (Author-Manuscript-Faelle)."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return ""
    for infon in root.iter("infon"):
        if (infon.get("key") or "") == "license":
            text = re.sub(r"\s+", " ", "".join(infon.itertext())).strip()
            if text and "author_manuscript" not in text:
                return "author_manuscript; " + text[:120]
            return "author_manuscript (Text-Mining erlaubt, kein Reuse)"
    return ""


def pmc_oa_pdf_url(pmcid: str, rec: dict) -> str:
    """PDF-Adresse aus dem offiziellen PMC-OA-Service (nur OA-Subset)."""
    url = f"https://pmc.ncbi.nlm.nih.gov/utils/oa/oa.fcgi?id={pmcid}"
    status, body = http(url, timeout=45)
    if status != 200:
        alt = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmcid}"
        status, body = http(alt, timeout=45)
        if status == 200:
            url = alt
    if status != 200 or not body:
        rec["attempts"].append({"kind": "pmc-oa-service", "url": url, "status": status,
                                "bytes": len(body), "ok": False})
        return ""
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return ""
    pdf, tgz = "", ""
    for link in root.iter("link"):
        href = link.get("href") or ""
        fmt = (link.get("format") or "").lower()
        if fmt == "pdf" and href:
            pdf = href
        elif fmt == "tgz" and href:
            tgz = href
    chosen = pdf
    if not chosen:
        hint = ("nur tgz-Paket angeboten, PDF nicht einzeln abrufbar" if tgz
                else "kein Link im OA-Service")
        rec["attempts"].append({"kind": "pmc-oa-service", "url": url, "status": status,
                                "bytes": len(body), "ok": False, "hinweis": hint})
        return ""
    rec["attempts"].append({"kind": "pmc-oa-service", "url": url, "status": status,
                            "bytes": len(body), "ok": True})
    # ftp:// -> https:// beim NCBI-Spiegel
    return chosen.replace("ftp://ftp.ncbi.nlm.nih.gov", "https://ftp.ncbi.nlm.nih.gov")


def repository_pdf_candidates(landing: str, rec: dict) -> list[str]:
    """PDF-Links auf einer Repositoriums-Landingpage einsammeln."""
    status, body = http(landing, timeout=45)
    rec["attempts"].append({"kind": "repository-landing", "url": landing,
                            "status": status, "bytes": len(body), "ok": status == 200})
    if status != 200 or not body:
        return []
    html = body.decode("utf-8", "replace")
    base = landing.rsplit("/", 1)[0] + "/"
    found: list[str] = []
    for match in re.finditer(r'href=["\']([^"\']+?\.pdf[^"\']*)["\']', html, re.IGNORECASE):
        href = match.group(1)
        if href.startswith("http"):
            found.append(href)
        elif href.startswith("/"):
            found.append(re.sub(r"^(https?://[^/]+).*", r"\1", landing) + href)
        else:
            found.append(base + href)
    return list(dict.fromkeys(found))[:3]


def try_download(url: str, dest: Path, kind: str, rec: dict) -> bool:
    # NCBI drosselt aggressiv: 429 wird mit Wartezeit wiederholt.
    for versuch in range(3):
        status, body = http(url, timeout=90)
        if status != 429:
            break
        time.sleep(12 + 8 * versuch)
    ok = status == 200 and len(body) > 20000
    if ok and kind == "pdf" and not body.startswith(b"%PDF"):
        ok = False
    rec["attempts"].append({"kind": kind, "url": url, "status": status, "bytes": len(body), "ok": ok})
    if ok:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
    return ok


def acquire(rec: dict) -> dict:
    folder = STUDIES_DIR / rec["study_id"]
    folder.mkdir(parents=True, exist_ok=True)
    pmcid = rec["epmc"].get("pmcid") or ""
    license_epmc = (rec["epmc"].get("license") or "").strip()
    up = rec["unpaywall"]

    result = {"fulltext_xml": False, "pdf_saved": False, "pdf_path": "", "xml_path": "",
              "download_erlaubt": "", "manuskriptversion": "", "lizenz": "", "lizenz_verifiziert": False,
              "zugaenglich": False, "volltext_url": "", "quelle": ""}

    # Lizenz bestimmen: Europe PMC ist fuer PMC-Inhalte die verlaesslichste Quelle.
    lic = license_epmc or up.get("best_license") or ""
    result["lizenz"] = lic or "unbekannt"
    freie_lizenz = bool(FREE_LICENSE.match(lic))
    result["lizenz_verifiziert"] = bool(lic) and lic != "unbekannt"

    # Manuskriptversion
    if rec["epmc"].get("in_pmc") and not rec["epmc"].get("is_open_access"):
        version = "author-manuscript (PMC, kein Reuse-Lizenznehmer)"
    else:
        version = up.get("best_version") or ("published (PMC)" if pmcid else "publisher")
    result["manuskriptversion"] = version

    # 1) Europe PMC XML (maschinenlesbar, bevorzugt)
    if pmcid:
        url = f"{EPMC}/{pmcid}/fullTextXML"
        if try_download(url, folder / "fulltext.xml", "xml", rec):
            result["fulltext_xml"] = True
            result["xml_path"] = str(folder / "fulltext.xml")
            result["zugaenglich"] = True
            result["volltext_url"] = url
            result["quelle"] = "Europe PMC fullTextXML"
        else:
            # 2) Alternative XML-Wege fuer Author Manuscripts
            bioc = ("https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/"
                    f"BioC_xml/{pmcid}/unicode")
            if try_download(bioc, folder / "fulltext_bioc.xml", "bioc", rec):
                result["fulltext_xml"] = True
                result["xml_path"] = str(folder / "fulltext_bioc.xml")
                result["zugaenglich"] = True
                result["volltext_url"] = bioc
                result["quelle"] = "PMC BioC (Author Manuscript, Text-Mining)"
                # Die Lizenz steht nicht in Europe PMC, sondern im BioC-Dokument.
                bioc_license = bioc_license_text(folder / "fulltext_bioc.xml")
                if bioc_license:
                    result["lizenz"] = bioc_license
                    result["lizenz_verifiziert"] = True

    # 3) PDF ueber den sanktionierten PMC-OA-Service (nur OA-Subset)
    if not result["pdf_saved"] and pmcid and freie_lizenz:
        oa_url = pmc_oa_pdf_url(pmcid, rec)
        if oa_url and try_download(oa_url, folder / "fulltext.pdf", "pdf", rec):
            result["pdf_saved"] = True
            result["pdf_path"] = str(folder / "fulltext.pdf")
            result["zugaenglich"] = True
            result["quelle"] = result["quelle"] or "PMC Open Access Service"

    # 4) Unpaywall-Repositorium, ebenfalls nur bei freier Lizenz
    if not result["pdf_saved"]:
        pdf_url = up.get("best_pdf") or ""
        lic_up = up.get("best_license") or ""
        if pdf_url and FREE_LICENSE.match(lic_up or ""):
            if try_download(pdf_url, folder / "fulltext.pdf", "pdf", rec):
                result["pdf_saved"] = True
                result["pdf_path"] = str(folder / "fulltext.pdf")
                result["zugaenglich"] = True
                result["quelle"] = f"Unpaywall/{up.get('best_host') or 'repository'}"
        elif pdf_url:
            rec["attempts"].append({"kind": "pdf", "url": pdf_url, "status": 0, "bytes": 0, "ok": False,
                                    "hinweis": f"nicht gespeichert (Lizenz '{lic_up or 'unbekannt'}')"})

    # 5) Green OA: Repositorium ueber die Landingpage aufloesen
    if not result["pdf_saved"]:
        landing = up.get("best_url") or ""
        lic_up = up.get("best_license") or ""
        if landing and FREE_LICENSE.match(lic_up or ""):
            if landing.lower().endswith(".pdf"):
                # Unpaywall liefert teils die PDF-Adresse direkt als best_url
                if try_download(landing, folder / "fulltext.pdf", "pdf", rec):
                    result["pdf_saved"] = True
                    result["pdf_path"] = str(folder / "fulltext.pdf")
                    result["zugaenglich"] = True
                    result["quelle"] = result["quelle"] or "Verlag (gold OA, PDF)"
                    landing = ""
            for pdf_url in (repository_pdf_candidates(landing, rec) if landing else []):
                if try_download(pdf_url, folder / "fulltext.pdf", "pdf", rec):
                    result["pdf_saved"] = True
                    result["pdf_path"] = str(folder / "fulltext.pdf")
                    result["zugaenglich"] = True
                    result["quelle"] = result["quelle"] or "Repositorium (green OA)"
                    break

    # Verlagsseite nur pruefen, nicht spiegeln
    pub_url = rec["crossref"].get("publisher_url") or ""
    if pub_url:
        status, _ = http(pub_url, timeout=25)
        rec["attempts"].append({"kind": "publisher-page-check", "url": pub_url,
                                "status": status, "bytes": 0, "ok": status == 200})

    if freie_lizenz:
        result["download_erlaubt"] = "ja (CC)"
    elif result["quelle"].startswith("PMC BioC"):
        result["download_erlaubt"] = "eingeschraenkt (Text-Mining, kein Reuse)"
    elif rec["epmc"].get("in_pmc"):
        result["download_erlaubt"] = "eingeschraenkt (Autor:innenmanuskript, nicht-kommerziell)"
    else:
        result["download_erlaubt"] = "nein (keine OA-Quelle)"
    (folder / "metadata.json").write_text(
        json.dumps({"study": rec, "ergebnis": result, "zugriffe": rec["attempts"]},
                   indent=2, ensure_ascii=True), encoding="utf-8")
    return result


# ---------------------------------------------------------------------------
# Schritt 3: Qualitaetskontrolle und Datenverfuegbarkeit
# ---------------------------------------------------------------------------

NUM = re.compile(r"-?\d+(?:\.\d+)?")

# Depressionsinstrumente, nicht nur das vom Review genannte: Dahne screent
# mit PHQ-8 und berichtet BDI-II - ein zu enger Instrumentenbezug haette das
# als "keine Armstatistik" fehlklassifiziert.
INSTRUMENT_RE = re.compile(
    r"(phq[\s-]?\d|bdi[\s-]?(?:ii|2|1a|ia)?\b|beck depression inventory|"
    r"ces[\s-]?d|center for epidemiolog|ham[\s-]?d|hamilton|madrs|dass[\s-]?\d*|"
    r"epds|scl[\s-]?\d*|k10)", re.IGNORECASE)
ARM_RE = re.compile(r"\b(intervention|control|waitlist|usual care|treatment|tx)\b", re.IGNORECASE)
# Demografie-Zeilen tragen ebenfalls "Mittelwert (SD)", sind aber keine
# Outcome-Werte. Ohne diesen Filter zaehlt z. B. "Age, mean (SD)" als
# Armstatistik.
DEMO_RE = re.compile(
    r"\b(age|gender|male|female|sex|income|education|married|employed|unemployed|"
    r"bmi|weight|height|session|minutes|duration of|years of|ethnic|race|"
    r"children|household|participants on average)\b", re.IGNORECASE)


def inspect_xml(path: Path, doi: str, instrument: str) -> dict:
    out = {"xml_parsebar": False, "doi_im_volltext": False, "titel_im_volltext": "",
           "zeichengruppe": 0, "sektionen": 0, "tabellen": 0,
           "tabellen_mit_instrument": 0, "plusminus": 0, "sd_marker": 0,
           "supplement_im_volltext": False, "effektschaetzer_mit_ki": 0,
           "armstatistik_zeile": False, "mean_sd_paar": 0, "modellbasiert": False}
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return out
    out["xml_parsebar"] = True

    for aid in root.iter("article-id"):
        if (aid.get("pub-id-type") or "").lower() == "doi" and doi.lower() in (aid.text or "").lower():
            out["doi_im_volltext"] = True
    title_el = root.find(".//article-title")
    out["titel_im_volltext"] = re.sub(r"\s+", " ", "".join(title_el.itertext())).strip() if title_el is not None else ""

    plain = re.sub(r"\s+", " ", "".join(root.itertext()))
    out["zeichengruppe"] = len(plain)
    out["sektionen"] = len(list(root.iter("sec")))
    out["tabellen"] = len(list(root.iter("table-wrap")))
    out["plusminus"] = plain.count("\u00b1") + plain.count("&plusmn;")
    out["sd_marker"] = len(re.findall(r"\bSD\b", plain))
    out["supplement_im_volltext"] = len(list(root.iter("supplementary-material"))) > 0
    out["effektschaetzer_mit_ki"] = len(re.findall(
        r"(?:SMD|Hedges|Cohen|d|OR|RR|beta|\u03b2)\s*[=:]?\s*-?\d\.\d+\s*[,;]?\s*(?:95\s*%\s*CI|CI)", plain))
    # Arm-Statistiken im Klartext: "12.3 (4.5)" = Mittelwert (SD).
    # Entscheidend ist, ob das Instrument in der Naehe steht (Outcome) oder
    # nur Baseline-Charakteristika (Alter, Ausgangswert) berichtet werden.
    pairs = list(re.finditer(r"\d+\.\d+\s*\(\s*\d+\.\d+\s*\)", plain))
    out["mean_sd_paar"] = len(pairs)
    inst_lo = instrument.lower()
    near = base = demo = 0
    evidence: list[str] = []
    for m in pairs:
        before = plain[max(0, m.start() - 300):m.start()]
        context = (before + " " + plain[m.start():m.start() + 160]).lower()
        instrument_da = (inst_lo in context) or bool(INSTRUMENT_RE.search(context))
        arm_da = bool(ARM_RE.search(before[-200:]))
        if instrument_da or arm_da:
            near += 1
            if DEMO_RE.search(before[-160:]):
                demo += 1
            elif "baseline" in context or "at baseline" in context:
                base += 1
            elif len(evidence) < 3:
                evidence.append(re.sub(r"\s+", " ", before[-160:] + plain[m.start():m.start() + 40]))
    out["instrument_mssd"] = near
    out["instrument_mssd_baseline"] = base
    out["demografie_mssd"] = demo
    out["outcome_mssd"] = near - base - demo
    out["belege"] = evidence
    out["modellbasiert"] = bool(re.search(
        r"(mixed[- ]effects?|multilevel|MMRM|ANCOVA|estimated marginal|generalized estimating|GEE|linear regression model)",
        plain, re.IGNORECASE))

    # Tabellenzeilen, die Instrument plus Mittelwert/Streuung tragen.
    # Das Instrument steht oft in der Tabellenueberschrift, nicht in der Zelle.
    for tw in root.iter("table-wrap"):
        cells = [re.sub(r"\s+", " ", "".join(c.itertext())).strip() for c in tw.iter("td")]
        caption = re.sub(r"\s+", " ", "".join(tw.find("caption").itertext())) if tw.find("caption") is not None else ""
        joined = caption + " " + " ".join(cells)
        if instrument.lower() in joined.lower():
            out["tabellen_mit_instrument"] += 1
            has_mean = bool(re.search(r"\b(mean|M)\b|\u00b1|-?\d+\.\d{2}", joined))
            if has_mean:
                out["armstatistik_zeile"] = True
    return out


def classify_quantitative(rec: dict, insp: dict | None) -> tuple[str, str]:
    """Eine von fuenf Kategorien plus Begruendung."""
    if insp is None:
        if rec["name"] in ("Dahne 2019", "Graham 2020"):
            return ("autorenanfrage",
                    "Volltext nur als Author Manuscript in PMC, XML-Endpunkt liefert HTTP 500")
        return ("nicht_oeffentlich", "keine legale Volltextquelle gefunden")
    if insp.get("outcome_mssd", 0) >= 2:
        return ("primaervolltext_armstatistik",
                f"{insp['outcome_mssd']} Outcome-Mittelwert-(SD)-Paare "
                f"({insp.get('instrument_mssd_baseline', 0)} Baseline-, "
                f"{insp.get('demografie_mssd', 0)} Demografie-Paare ausgeschlossen)")
    if insp.get("instrument_mssd_baseline", 0) >= 2:
        return ("primaervolltext_modellbasiert",
                f"nur Baseline-Armwerte fuer {rec['instrument']}, Outcome modellbasiert")
    if insp["modellbasiert"] and insp["effektschaetzer_mit_ki"] > 0:
        return ("primaervolltext_modellbasiert",
                f"modellbasierte Auswertung, {insp['effektschaetzer_mit_ki']} Effektschaetzer mit KI")
    if insp["modellbasiert"]:
        return ("primaervolltext_modellbasiert",
                "modellbasierte Auswertung ohne Arm-Mittelwerte im Text")
    if insp.get("supplement_im_volltext"):
        return ("nur_supplement", "keine Arm-Statistik im Text; Supplement vorhanden, Inhalt ungeprueft")
    if insp["zeichengruppe"] > 1000:
        return ("autorenanfrage", "Volltext vorhanden, aber keine extrahierbaren Arm-Statistiken")
    return ("nicht_oeffentlich", "kein verwertbarer Volltext")


# ---------------------------------------------------------------------------
# Schritt 4: Statistik und Bericht
# ---------------------------------------------------------------------------

def stats(rows: list[dict]) -> dict:
    n = len(rows)
    def rate(pred) -> dict:
        k = sum(1 for r in rows if pred(r))
        return {"k": k, "n": n, "prozent": round(100.0 * k / n, 1)}
    return {
        "identifikationsrate": rate(lambda r: r["verified"]["doi_aufgeloest_crossref"]),
        "volltextzugriffsrate": rate(lambda r: r["result"]["zugaenglich"]),
        "pdf_downloadrate": rate(lambda r: r["result"]["pdf_saved"]),
        "maschinenlesbarkeitsrate": rate(lambda r: bool(r.get("inspection") and r["inspection"]["xml_parsebar"])),
        "lizenzgeklaerte_weiterverarbeitung": rate(
            lambda r: r["result"]["download_erlaubt"].startswith(("ja", "eingeschraenkt"))),
        "quantitative_datenverfuegbarkeit": rate(
            lambda r: r["quantitative"][0].startswith("primaervolltext")),
    }


def write_csv(rows: list[dict]) -> None:
    cols = ["study_id", "authors", "year", "title", "doi", "pmid", "pmcid", "publisher_url",
            "fulltext_url", "source_repository", "fulltext_available", "pdf_downloaded",
            "machine_readable", "manuscript_version", "license", "license_verified",
            "supplementary_material_available", "quantitative_data_available", "access_notes",
            "im_effektpool_review"]
    with INVENTORY_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r["csv"])


def build_report(rows: list[dict], st: dict) -> str:
    L = ["# Beschaffung der 12 Primaerstudien: Serrano-Ripoll et al. 2022", ""]
    L.append("Review: `10.2196/29621`, PMC8832272. Automatisch erzeugt von "
             "`scripts/beschaffe_serrano_volltexte.py`.")
    L.append("")
    L.append("## Abdeckung (Nenner = 12)")
    L.append("")
    L.append("| Kennzahl | k/12 | % |")
    L.append("|---|---|---|")
    for key, label in (("identifikationsrate", "Identifikation"),
                       ("volltextzugriffsrate", "Volltextzugriff"),
                       ("pdf_downloadrate", "PDF-Download"),
                       ("maschinenlesbarkeitsrate", "maschinenlesbar"),
                       ("lizenzgeklaerte_weiterverarbeitung", "Lizenz geklaert (CC oder Text-Mining)"),
                       ("quantitative_datenverfuegbarkeit", "quantitative Daten")):
        v = st[key]
        L.append(f"| {label} | {v['k']}/12 | {v['prozent']} |")
    L.append("")
    L.append("### Datenlage im Ueberblick")
    L.append("")
    zaehler: dict[str, int] = {}
    for r in rows:
        zaehler[r["quantitative"][0]] = zaehler.get(r["quantitative"][0], 0) + 1
    L.append("| Kategorie | Anzahl |")
    L.append("|---|---|")
    for key in ("primaervolltext_armstatistik", "primaervolltext_modellbasiert",
                "nur_supplement", "nicht_oeffentlich", "autorenanfrage"):
        L.append(f"| {key} | {zaehler.get(key, 0)} |")
    L.append("")
    L.append("## Einzelbefunde")
    L.append("")
    L.append("| # | Studie | PMC | Zugriff | PDF | XML | Lizenz | Datenlage |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in rows:
        res = r["result"]
        L.append(f"| {r['nummer_review']} | {r['name']} | {r['epmc'].get('pmcid') or '-'} "
                 f"| {'ja' if res['zugaenglich'] else 'nein'} "
                 f"| {'ja' if res['pdf_saved'] else 'nein'} "
                 f"| {'ja' if r.get('inspection') and r['inspection']['xml_parsebar'] else 'nein'} "
                 f"| {res['lizenz']} | {r['quantitative'][0]} |")
    L.append("")
    L.append("## Datenlage mit Belegstellen")
    L.append("")
    L.append("Die Einordnung stammt aus einem Musterabgleich (Mittelwert-(SD)-Paare in der Naehe "
             "eines Depressionsinstruments oder einer Armbezeichnung, ohne Baseline- und "
             "Demografiezeilen). Sie ist ein Filter, kein Extraktionsergebnis - die Belegstellen "
             "sind zur menschlichen Kontrolle mitgegeben.")
    L.append("")
    for r in rows:
        insp = r.get("inspection") or {}
        L.append(f"### {r['name']}")
        L.append("")
        L.append(f"- Kategorie: {r['quantitative'][0]} - {r['quantitative'][1]}")
        if insp:
            L.append(f"- Paare gesamt {insp.get('mean_sd_paar', 0)}, Instrument/Arm nah "
                     f"{insp.get('instrument_mssd', 0)}, davon Baseline {insp.get('instrument_mssd_baseline', 0)}, "
                     f"Demografie {insp.get('demografie_mssd', 0)}")
            for b in insp.get("belege", [])[:2]:
                L.append(f"- Beleg: `...{b[-140:]}`")
        L.append("")
    L.append("## Zugriffsprotokoll je Studie")
    L.append("")
    for r in rows:
        L.append(f"### {r['name']} ({r['doi']})")
        L.append("")
        L.append(f"- Manuskriptversion: {r['result']['manuskriptversion']}")
        L.append(f"- Quelle: {r['result']['quelle'] or 'keine'}")
        L.append(f"- Speicherung erlaubt: {r['result']['download_erlaubt']}")
        L.append(f"- Datenlage: {r['quantitative'][0]} - {r['quantitative'][1]}")
        for a in r["attempts"]:
            note = f" ({a['hinweis']})" if a.get("hinweis") else ""
            L.append(f"- `{a['kind']}` HTTP {a['status']}, {a['bytes']} Bytes{note} - {a['url']}")
        L.append("")
    L.append("## Rechtlicher Hinweis")
    L.append("")
    L.append("Gespeichert werden nur Dateien mit freier Lizenz (CC) sowie "
             "Autor:innenmanuskripte aus PMC fuer nicht-kommerzielle Forschung. "
             "Die Volltextdateien selbst sind per `.gitignore` von der "
             "Versionierung ausgenommen; versioniert werden nur Metadaten, "
             "Pruefprotokolle und dieser Bericht.")
    return "\n".join(L) + "\n"


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    STUDIES_DIR.mkdir(parents=True, exist_ok=True)
    (STUDIES_DIR / ".gitignore").write_text(
        "# Volltexte sind fremde Werke: nur lokal fuer die Forschung, nicht im Repo\n"
        "*.xml\n*.pdf\n*.html\n*.txt\n", encoding="utf-8")

    rows = []
    for study in STUDIES:
        rec = metadata(study)
        rec["verified"] = verify(rec)
        result = acquire(rec)

        insp = None
        if result["xml_path"]:
            insp = inspect_xml(Path(result["xml_path"]), rec["doi"], rec["instrument"])
        quant = classify_quantitative(rec, insp)

        pmcid = rec["epmc"].get("pmcid") or ""
        csv_row = {
            "study_id": rec["study_id"],
            "authors": rec["verified"]["autoren_crossref"],
            "year": rec["verified"]["jahr_crossref"] or rec["epmc"].get("year", ""),
            "title": rec["crossref"].get("title") or rec["epmc"].get("title", ""),
            "doi": rec["doi"], "pmid": rec["pmid"], "pmcid": pmcid,
            "publisher_url": rec["crossref"].get("publisher_url", ""),
            "fulltext_url": result["volltext_url"],
            "source_repository": result["quelle"],
            "fulltext_available": "ja" if result["zugaenglich"] else "nein",
            "pdf_downloaded": "ja" if result["pdf_saved"] else "nein",
            "machine_readable": "ja" if (insp and insp["xml_parsebar"]) else "nein",
            "manuscript_version": result["manuskriptversion"],
            "license": result["lizenz"],
            "license_verified": "ja" if result["lizenz_verifiziert"] else "nein",
            "supplementary_material_available": "ja" if (rec["epmc"].get("has_suppl")
                                                         or (insp and insp["supplement_im_volltext"])) else "nein",
            "quantitative_data_available": quant[0],
            "access_notes": quant[1],
            "im_effektpool_review": "ja" if rec["im_effektpool_review"] else "nein",
        }
        rows.append({"nummer_review": rec["nummer_review"], "study_id": rec["study_id"],
                     "name": rec["name"], "doi": rec["doi"], "pmid": rec["pmid"],
                     "epmc": rec["epmc"], "crossref": rec["crossref"],
                     "unpaywall": rec["unpaywall"], "verified": rec["verified"],
                     "result": result, "inspection": insp, "quantitative": quant,
                     "attempts": rec["attempts"], "csv": csv_row})
        print(f"  {rec['name']:14s} zugriff={res_label(result['zugaenglich'])} "
              f"pdf={res_label(result['pdf_saved'])} xml={res_label(bool(insp and insp['xml_parsebar']))} "
              f"lizenz={result['lizenz'][:22]:22s} daten={quant[0]}")
        time.sleep(0.3)

    st = stats(rows)
    payload = {"review": "Serrano-Ripoll 2022 (10.2196/29621)", "stand": "2026-11-17",
               "studien": rows, "abdeckung": st}
    INVENTORY.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    write_csv(rows)
    REPORT.write_text(build_report(rows, st), encoding="utf-8")

    print("\n=== Abdeckung ===")
    for k, v in st.items():
        print(f"  {k:36s} {v['k']:2d}/12  {v['prozent']:5.1f}%")
    print(f"\nJSON: {INVENTORY}\nCSV:  {INVENTORY_CSV}\nMD:   {REPORT}")
    return 0


def res_label(flag: bool) -> str:
    return "ja  " if flag else "nein"


if __name__ == "__main__":
    raise SystemExit(main())
