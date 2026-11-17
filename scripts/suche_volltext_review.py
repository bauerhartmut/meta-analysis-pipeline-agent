"""Sucht Metaanalysen, deren Primaerstudien vollstaendig offen sind.

Vorgehen: Europe PMC nach Kandidaten-Reviews durchsuchen, aus dem Volltext-XML
die im Results-Teil zitierten Referenzen ziehen (das sind bei einer
Systematik die eingeschlossenen Studien, waehrend Einleitung und Diskussion
Hintergrundliteratur zitieren), und fuer diese Referenzen den OA-Status
sammeln.

Read-only gegen oeffentliche APIs. Ausgabe ASCII.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
UA = "AIResearch-Reproduzierbarkeit/1.0 (mailto:research@freebuff.ai)"
OUT = Path("data/reviews/volltext_review_kandidaten_20261117.json")
TAG = "_" + "_".join(sys.argv[1:]) if len(sys.argv) > 1 else ""

# Themenfelder, in denen Primaerstudien ueberwiegend in OA-Journalen
# erscheinen (JMIR, Frontiers, BMC, PLOS, BMJ Open) oder unter
# Foerderermandat stehen (COVID-19).
QUERIES = {
    "digital": ('(TITLE:"app" OR TITLE:"mHealth" OR TITLE:"digital" OR TITLE:"smartphone") '
                'AND (PUB_TYPE:"Meta-Analysis") AND (OPEN_ACCESS:y) AND (HAS_FT:y) '
                'AND (PUB_YEAR:[2021 TO 2026])'),
    "covid": ('(TITLE:"COVID-19" OR TITLE:"SARS-CoV-2") AND (PUB_TYPE:"Meta-Analysis") '
              'AND (OPEN_ACCESS:y) AND (HAS_FT:y) AND (PUB_YEAR:[2021 TO 2026])'),
    "telehealth": ('(TITLE:"telehealth" OR TITLE:"telemedicine" OR TITLE:"eHealth") '
                   'AND (PUB_TYPE:"Meta-Analysis") AND (OPEN_ACCESS:y) AND (HAS_FT:y) '
                   'AND (PUB_YEAR:[2021 TO 2026])'),
    "student": ('(TITLE:"students" OR TITLE:"university") AND (PUB_TYPE:"Meta-Analysis") '
                'AND (OPEN_ACCESS:y) AND (HAS_FT:y) AND (PUB_YEAR:[2021 TO 2026])'),
}

RESULTS_SEC = re.compile(r"result|finding|outcome", re.IGNORECASE)
INCLUDED_TABLE = re.compile(r"included stud|characteristic|study characteristic", re.IGNORECASE)
MAX_CANDIDATES = 18


def http(url: str, timeout: int = 45) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except Exception:  # noqa: BLE001
        return 0, b""


def get_json(url: str, timeout: int = 45):
    status, body = http(url, timeout)
    if status != 200 or not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def flat(el) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip() if el is not None else ""


def find_candidates(topics: list[str]) -> list[dict]:
    seen: dict[str, dict] = {}
    for topic in topics:
        query = QUERIES[topic]
        q = urllib.parse.quote(query)
        data = get_json(f"{EPMC}/search?query={q}&resultType=lite&format=json&pageSize=60") or {}
        for rec in (data.get("resultList") or {}).get("result") or []:
            pmid = rec.get("pmid") or ""
            pmcid = rec.get("pmcid") or ""
            if not pmid or not pmcid or pmid in seen:
                continue
            seen[pmid] = {"pmid": pmid, "pmcid": pmcid,
                          "title": rec.get("title") or "",
                          "journal": rec.get("journalTitle") or "",
                          "year": rec.get("pubYear") or ""}
        time.sleep(0.4)
    return list(seen.values())


def cited_primary_refs(pmcid: str) -> tuple[list[str], dict[str, str], int]:
    """Referenzen, die im Results-Teil oder in der Einschlusstabelle zitiert werden."""
    status, body = http(f"{EPMC}/{pmcid}/fullTextXML", timeout=60)
    if status != 200 or not body:
        return [], {}, status
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return [], {}, -1

    cited: list[str] = []
    for sec in root.iter("sec"):
        if RESULTS_SEC.search(flat(sec.find("title"))):
            for xref in sec.iter("xref"):
                if (xref.get("ref-type") or "") == "bibr":
                    cited.append(xref.get("rid") or "")
    for tw in root.iter("table-wrap"):
        if INCLUDED_TABLE.search(flat(tw.find("caption"))):
            for xref in tw.iter("xref"):
                if (xref.get("ref-type") or "") == "bibr":
                    cited.append(xref.get("rid") or "")

    doi_by_rid: dict[str, str] = {}
    for ref in root.iter("ref"):
        rid = ref.get("id") or ""
        doi = ""
        for pid in ref.iter("pub-id"):
            if (pid.get("pub-id-type") or "").lower() == "doi":
                doi = (pid.text or "").strip().lower()
                break
        if rid and doi:
            doi_by_rid[rid] = doi

    ordered = [r for r in dict.fromkeys(cited) if r]
    return ordered, doi_by_rid, status


def oa_status(dois: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for start in range(0, len(dois), 20):
        chunk = dois[start:start + 20]
        query = " OR ".join(f'DOI:"{d}"' for d in chunk)
        q = urllib.parse.quote(query)
        data = get_json(f"{EPMC}/search?query={q}&resultType=lite&format=json"
                        f"&pageSize={len(chunk) + 10}") or {}
        for rec in (data.get("resultList") or {}).get("result") or []:
            doi = (rec.get("doi") or "").lower()
            if doi:
                out[doi] = {"is_open_access": rec.get("isOpenAccess") == "Y",
                            "in_pmc": rec.get("inPMC") == "Y",
                            "title": rec.get("title") or ""}
        time.sleep(0.4)
    return out


def main() -> int:
    topics = sys.argv[1:] or list(QUERIES)
    topics = [t for t in topics if t in QUERIES]
    print(f"Kandidaten sammeln fuer {topics} ...")
    candidates = find_candidates(topics)
    print(f"  {len(candidates)} Kandidaten mit Volltext in Europe PMC")

    rows = []
    for cand in candidates[:MAX_CANDIDATES]:
        refs, doi_by_rid, status = cited_primary_refs(cand["pmcid"])
        if status != 200:
            print(f"  {cand['pmid']}: XML HTTP {status} - uebersprungen")
            continue
        dois = [doi_by_rid[r] for r in refs if r in doi_by_rid]
        dois = list(dict.fromkeys(dois))
        if len(dois) < 4:
            print(f"  {cand['pmid']}: nur {len(dois)} zitierte Primaer-DOIs - uebersprungen")
            continue
        oa = oa_status(dois)
        oa_yes = [d for d in dois if oa.get(d, {}).get("is_open_access")]
        pmc_yes = [d for d in dois if oa.get(d, {}).get("in_pmc")]
        missing = [d for d in dois if d not in oa]
        row = dict(cand, k=len(dois), oa_cc=len(oa_yes), oa_cc_by=len(pmc_yes),
                   nicht_indexiert=len(missing),
                   offene_luecke=[d for d in dois if not oa.get(d, {}).get("is_open_access")][:12],
                   erste_titel=[oa.get(d, {}).get("title", d)[:60] for d in dois[:6]])
        rows.append(row)
        print(f"  {cand['pmid']} k={row['k']:2d} CC-BY={row['oa_cc']:2d} inPMC={row['oa_cc_by']:2d} "
              f"| {cand['title'][:58]}")

    rows.sort(key=lambda r: (-(r["oa_cc"] / max(r["k"], 1)), r["k"]))
    print("\n=== Rangliste nach CC-BY-Anteil ===")
    for r in rows[:8]:
        pct = 100.0 * r["oa_cc"] / r["k"]
        print(f"{pct:5.1f}%  k={r['k']:2d}  CC-BY={r['oa_cc']:2d}  inPMC={r['oa_cc_by']:2d}  "
              f"{r['year']}  {r['pmid']}  {r['title'][:56]}")
        if r["offene_luecke"]:
            print(f"        offen: {', '.join(r['offene_luecke'][:4])}")

    out_path = OUT.with_name(OUT.stem + TAG + OUT.suffix)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
