"""Prueft die Reproduzierbarkeit der Referenzliste von Serrano-Ripoll 2022.

Zwei Fragen, beide read-only gegen oeffentliche APIs:

1. Sind die 12 eingeschlossenen RCTs ueber die Provider des Agenten
   (Europe PMC, PubMed, Crossref, OpenAlex, Semantic Scholar) erreichbar,
   obwohl Embase, PsycINFO, CINAHL und CENTRAL fehlen?
   - Identifier-Ebene: ist die Studie im Korpus des Providers enthalten?
   - Such-Ebene: taucht sie bei einer realistischen Stichwortsuche auf?
2. Lassen sich Arm-Statistiken (Mittelwert + SD) aus den offenen
   Volltexten ziehen?

Kein Modellaufruf, keine Datenbank, keine Schreibzugriffe ausser der
JSON-Datei. Ausgabe ist ASCII, damit die Windows-Konsole nicht bricht.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
UA = "AIResearch-Reproduzierbarkeit/1.0 (mailto:research@freebuff.ai)"
MAILTO = "research@freebuff.ai"
OUT = Path("data/reviews/serrano_referenzen_20261117.json")

# Die 12 eingeschlossenen Studien, identifiziert ueber PMID (aus dem
# References-Endpunkt des Reviews) und das jeweilige Primaerinstrument.
STUDIES = [
    ("Arean 2016", 27998876, "PHQ-9"),
    ("Birney 2016", 26813737, "PHQ-9"),
    ("Dahne 2019", 31208690, "PHQ-9"),
    ("Ham 2019", 31402881, "BDI-II"),
    ("Luedtke 2018", 30273901, "BDI-II"),
    ("Mantani 2017", 29101095, "BDI-II"),
    ("Moberg 2019", 31199319, "PHQ-8"),
    ("Pratap 2018", 30093372, "PHQ-9"),
    ("Roepke 2015", 26182069, "CES-D"),
    ("Tighe 2017", 28132007, "PHQ-9"),
    ("Graham 2020", 32432695, "PHQ-8"),
    ("Guo 2020", 32044751, "CES-D"),
]

# Realistische Suchanfrage: ein Konzeptpaar plus Designfilter, so wie der
# Planer des Agenten es bauen wuerde.
QUERY_PLAIN = "smartphone app depression randomized controlled trial"


def http(url: str, timeout: int = 30) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except Exception:  # noqa: BLE001 - Netzfehler sind hier Datenpunkte
        return 0, b""


def get_json(url: str, timeout: int = 30):
    status, body = http(url, timeout)
    if status != 200 or not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def norm_title(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


# ---------------------------------------------------------------------------
# Schritt 1: Identifier aufloesen (DOI/PMCID/OA-Status aus Europe PMC)
# ---------------------------------------------------------------------------

def resolve_identifiers() -> list[dict]:
    rows = []
    for name, pmid, instrument in STUDIES:
        url = f"{EPMC}/search?query=EXT_ID:{pmid}%20AND%20SRC:MED&resultType=lite&format=json"
        data = get_json(url) or {}
        hits = (data.get("resultList") or {}).get("result") or []
        if not hits:
            rows.append({"name": name, "pmid": pmid, "instrument": instrument,
                         "found_in_epmc": False})
            continue
        rec = hits[0]
        rows.append({
            "name": name,
            "pmid": pmid,
            "instrument": instrument,
            "found_in_epmc": True,
            "doi": (rec.get("doi") or "").lower(),
            "pmcid": rec.get("pmcid") or "",
            "is_open_access": rec.get("isOpenAccess") == "Y",
            "in_pmc": rec.get("inPMC") == "Y",
            "has_pdf": rec.get("hasPDF") == "Y",
            "title": rec.get("title") or "",
            "journal": rec.get("journalTitle") or "",
            "pub_year": rec.get("pubYear") or "",
        })
        time.sleep(0.2)
    return rows


# ---------------------------------------------------------------------------
# Schritt 2a: Identifier-Ebene - ist die Studie im Korpus des Providers?
# ---------------------------------------------------------------------------

def check_identifier(row: dict) -> dict:
    doi = row.get("doi") or ""
    out = {"europepmc_by_doi": None, "pubmed_by_doi": None,
           "crossref": None, "openalex": None, "semanticscholar": None}
    if not doi:
        return out

    q = urllib.parse.quote(f'DOI:"{doi}"')
    data = get_json(f"{EPMC}/search?query={q}&resultType=lite&format=json") or {}
    out["europepmc_by_doi"] = (data.get("hitCount") or 0) > 0
    time.sleep(0.2)

    term = urllib.parse.quote(f'"{doi}"[doi]')
    data = get_json(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pubmed&term={term}&retmode=json&rettype=count"
    )
    if data:
        out["pubmed_by_doi"] = int((data.get("esearchresult") or {}).get("count") or 0) > 0
    time.sleep(0.35)

    status, _ = http(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}?mailto={MAILTO}")
    out["crossref"] = status == 200

    data = get_json(f"https://api.openalex.org/works/doi:{doi}?mailto={MAILTO}")
    out["openalex"] = data is not None
    out["openalex_id"] = (data or {}).get("id") or ""

    time.sleep(3.2)  # Semantic Scholar: 1 Request pro 3 s im freien Kontingent
    data = get_json(
        "https://api.semanticscholar.org/graph/v1/paper/"
        f"DOI:{urllib.parse.quote(doi)}?fields=title,isOpenAccess,openAccessPdf"
    )
    out["semanticscholar"] = data is not None
    if data:
        out["s2_open_access_pdf"] = bool(data.get("openAccessPdf"))
    return out


# ---------------------------------------------------------------------------
# Schritt 2b: Such-Ebene - erscheint die Studie bei einer Stichwortsuche?
# ---------------------------------------------------------------------------

def keyword_recall(studies: list[dict], limit: int = 100) -> dict:
    """Ein Suchlauf je Provider; zaehlt, wie viele der 12 zurueckkommen."""
    result: dict[str, dict] = {}
    doi_set = {s["doi"] for s in studies if s.get("doi")}
    title_set = {norm_title(s["title"])[:70] for s in studies if s.get("title")}

    def score(found_dois: set[str], found_titles: set[str]) -> dict:
        by_doi = len(doi_set & found_dois)
        by_title = len(title_set & found_titles)
        return {"treffer": max(by_doi, by_title), "ueber_doi": by_doi,
                "ueber_titel": by_title, "von": len(doi_set)}

    # Europe PMC
    q = urllib.parse.quote('("smartphone app" OR "mobile app") AND (TITLE_ABS:"depression") '
                           'AND (TITLE_ABS:"randomized controlled trial")')
    data = get_json(f"{EPMC}/search?query={q}&resultType=lite&format=json&pageSize={limit}") or {}
    recs = (data.get("resultList") or {}).get("result") or []
    result["europepmc"] = score(
        {(r.get("doi") or "").lower() for r in recs},
        {norm_title(r.get("title") or "")[:70] for r in recs},
    )
    result["europepmc"]["hitCount"] = data.get("hitCount")
    result["europepmc"]["zurueckgegeben"] = len(recs)
    time.sleep(0.5)

    # PubMed
    term = urllib.parse.quote('("smartphone app"[tiab] OR "mobile app"[tiab]) '
                              'AND depression[tiab] AND randomized[tiab]')
    data = get_json(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pubmed&term={term}&retmode=json&retmax={limit}&sort=relevance"
    ) or {}
    ids = set((data.get("esearchresult") or {}).get("idlist") or [])
    pmid_set = {str(s["pmid"]) for s in studies}
    result["pubmed"] = {"treffer": len(ids & pmid_set), "von": len(pmid_set),
                        "hitCount": int((data.get("esearchresult") or {}).get("count") or 0),
                        "zurueckgegeben": len(ids)}
    time.sleep(0.5)

    # Crossref
    url = ("https://api.crossref.org/works?query=" + urllib.parse.quote(QUERY_PLAIN)
           + f"&rows={limit}&sort=relevance&mailto={MAILTO}")
    data = get_json(url) or {}
    items = (data.get("message") or {}).get("items") or []
    result["crossref"] = score(
        {(i.get("DOI") or "").lower() for i in items},
        {norm_title((i.get("title") or [""])[0])[:70] for i in items},
    )
    result["crossref"]["zurueckgegeben"] = len(items)

    # OpenAlex
    url = ("https://api.openalex.org/works?search=" + urllib.parse.quote(QUERY_PLAIN)
           + f"&per_page={limit}&sort=relevance_score:desc&mailto={MAILTO}")
    data = get_json(url) or {}
    items = data.get("results") or []
    result["openalex"] = score(
        {(i.get("doi") or "").replace("https://doi.org/", "").lower() for i in items},
        {norm_title(i.get("title") or "")[:70] for i in items},
    )
    result["openalex"]["zurueckgegeben"] = len(items)
    time.sleep(0.5)

    # Semantic Scholar
    time.sleep(3.2)
    url = ("https://api.semanticscholar.org/graph/v1/paper/search?query="
           + urllib.parse.quote(QUERY_PLAIN) + f"&limit={limit}&fields=title,externalIds")
    data = get_json(url) or {}
    items = data.get("data") or []
    result["semanticscholar"] = score(
        {((i.get("externalIds") or {}).get("DOI") or "").lower() for i in items},
        {norm_title(i.get("title") or "")[:70] for i in items},
    )
    result["semanticscholar"]["zurueckgegeben"] = len(items)
    return result


# ---------------------------------------------------------------------------
# Schritt 3: Extraktionstauglichkeit der offenen Volltexte
# ---------------------------------------------------------------------------

def rank_check(studies: list[dict], depth: int = 1000) -> dict:
    """Rang der Referenzstudie im Suchergebnis - ist sie nur weit hinten?"""
    out: dict[str, dict] = {}
    q = urllib.parse.quote('("smartphone app" OR "mobile app") AND (TITLE_ABS:"depression") '
                           'AND (TITLE_ABS:"randomized controlled trial")')
    data = get_json(f"{EPMC}/search?query={q}&resultType=lite&format=json&pageSize={depth}") or {}
    recs = (data.get("resultList") or {}).get("result") or []
    order = [(r.get("doi") or "").lower() for r in recs]
    out["europepmc"] = {"hitCount": data.get("hitCount"),
                        "raenge": {s["name"]: (order.index(s["doi"]) + 1
                                               if s.get("doi") in order else None)
                                   for s in studies}}
    time.sleep(0.5)

    term = urllib.parse.quote('("smartphone app"[tiab] OR "mobile app"[tiab]) '
                              'AND depression[tiab] AND randomized[tiab]')
    data = get_json(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pubmed&term={term}&retmode=json&retmax={depth}&sort=relevance"
    ) or {}
    ids = [str(i) for i in ((data.get("esearchresult") or {}).get("idlist") or [])]
    out["pubmed"] = {"hitCount": int((data.get("esearchresult") or {}).get("count") or 0),
                     "raenge": {s["name"]: (ids.index(str(s["pmid"])) + 1
                                            if str(s["pmid"]) in ids else None)
                                for s in studies}}
    return out


def citation_check(studies: list[dict]) -> dict:
    """Erreichbarkeit ueber den Zitationspfad: zitieren einschlaegige Reviews sie?"""
    wanted = {s["identifier"].get("openalex_id"): s["name"]
              for s in studies if s["identifier"].get("openalex_id")}
    out = {}
    for label, doi in (("Linardon 2019 (World Psychiatry)", "10.1002/wps.20673"),
                       ("Firth 2017 (World Psychiatry)", "10.1002/wps.20472")):
        data = get_json("https://api.openalex.org/works/doi:"
                        f"{doi}?mailto={MAILTO}&select=id,referenced_works,referenced_works_count")
        refs = set((data or {}).get("referenced_works") or [])
        hit = [wanted[i] for i in refs if i in wanted]
        out[label] = {"referenzen": (data or {}).get("referenced_works_count"),
                      "treffer": sorted(hit), "anzahl": len(hit), "von": len(wanted)}
        time.sleep(0.5)
    return out


def extraction_check(studies: list[dict]) -> list[dict]:
    rows = []
    for s in studies:
        pmcid = s.get("pmcid") or ""
        entry = {"name": s["name"], "pmcid": pmcid, "instrument": s["instrument"]}
        if not pmcid:
            entry["volltext"] = "kein PMC-Volltext"
            rows.append(entry)
            continue
        status, body = http(f"{EPMC}/{pmcid}/fullTextXML", timeout=60)
        if status != 200 or not body:
            entry["volltext"] = f"XML nicht abrufbar (HTTP {status})"
            rows.append(entry)
            continue
        text = body.decode("utf-8", "replace")
        plain = re.sub(r"<[^>]+>", " ", text)
        plain = re.sub(r"\s+", " ", plain)
        entry["volltext"] = "ok"
        entry["zeichen"] = len(plain)
        # Europe PMC liefert das Plusminus als XML-Entity, deshalb beide Formen.
        plusminus = len(re.findall(r"\u00b1\s*\d", plain)) + len(re.findall(r"&plusmn;\s*\d", text))
        entry["pm_vorkommen"] = plusminus
        entry["sd_vorkommen"] = len(re.findall(r"\bSD\b\s*[=:]?\s*\d", plain))
        entry["mean_vorkommen"] = len(re.findall(r"\b[Mm]ean\b\s*[=:(]?\s*-?\d+\.\d", plain))
        inst = re.escape(s["instrument"])
        entry["instrument_vorkommen"] = len(re.findall(inst, plain, re.IGNORECASE))
        # Tabellenzeilen mit Instrument und Zahl (typischer Extraktionsort)
        entry["instrument_mit_zahl"] = len(re.findall(
            inst + r"[^.]{0,120}?\d+\.\d+", plain, re.IGNORECASE))
        # Brauchbar, wenn irgendwo ein Mittelwert mit SD oder Plusminus steht.
        entry["arm_statistik_im_text"] = (plusminus > 0) or (
            entry["sd_vorkommen"] > 0 and entry["mean_vorkommen"] > 0)
        rows.append(entry)
        time.sleep(0.3)
    return rows


def main() -> int:
    print("Schritt 1: Identifier aufloesen ...")
    studies = resolve_identifiers()
    for s in studies:
        print(f"  {s['name']:14s} doi={s.get('doi', '-'):32s} pmcid={s.get('pmcid') or '-':12s} "
              f"OA={s.get('is_open_access')}")

    print("\nSchritt 2a: Identifier-Ebene je Provider ...")
    for s in studies:
        s["identifier"] = check_identifier(s)
        idt = s["identifier"]
        print(f"  {s['name']:14s} EPMC={idt['europepmc_by_doi']} PubMed={idt['pubmed_by_doi']} "
              f"Crossref={idt['crossref']} OpenAlex={idt['openalex']} S2={idt['semanticscholar']}")

    print("\nSchritt 2b: Stichwortsuche je Provider (Limit 100) ...")
    recall = keyword_recall(studies)
    for prov, stats in recall.items():
        print(f"  {prov:16s} {stats['treffer']}/{stats['von']} Treffer "
              f"(hitCount={stats.get('hitCount')}, zurueck={stats.get('zurueckgegeben')})")

    print("\nSchritt 2c: Rangposition im Suchergebnis (Tiefe 1000) ...")
    ranks = rank_check(studies)
    for prov, info in ranks.items():
        found = [f"{n}=#{r}" for n, r in info["raenge"].items() if r]
        print(f"  {prov:12s} hitCount={info['hitCount']} gefunden_im_fenster={len(found)}/12")
        print(f"    {', '.join(found) if found else '(keine)'}")

    print("\nSchritt 2d: Zitationspfad ueber einschlaegige Reviews ...")
    citation = citation_check(studies)
    for label, info in citation.items():
        print(f"  {label}: {info['anzahl']}/{info['von']} der 12 in der Referenzliste "
              f"(Review hat {info['referenzen']} Referenzen)")
        print(f"    {', '.join(info['treffer'])}")

    print("\nSchritt 3: Volltext-Extraktion ...")
    extraction = extraction_check(studies)
    for e in extraction:
        print(f"  {e['name']:14s} {e['volltext']:22s} zeichen={e.get('zeichen', 0):6d} "
              f"+-={e.get('pm_vorkommen', 0):3d} SD={e.get('sd_vorkommen', 0):3d} "
              f"mean={e.get('mean_vorkommen', 0):3d} "
              f"{e['instrument']}+Zahl={e.get('instrument_mit_zahl', 0)} "
              f"arm_statistik={e.get('arm_statistik_im_text')}")

    payload = {"review": "Serrano-Ripoll 2022 (10.2196/29621)", "studies": studies,
               "keyword_recall": recall, "ranks": ranks, "citation": citation,
               "extraction": extraction}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"\nJSON: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
