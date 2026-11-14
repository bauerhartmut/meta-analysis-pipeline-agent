#!/usr/bin/env python3
"""Laedt Artikel aus dem PMC-Open-Access-Bestand und extrahiert Tabellen.

Hintergrund: Die alten FTP-Pakete (``oa_file_list.csv``, ``oa_comm``) wurden
laut NCBI-Readme im August 2026 abgeschaltet. Der Bestand liegt jetzt im
oeffentlichen S3-Bucket ``pmc-oa-opendata``; je Artikel gibt es ein
versioniertes Verzeichnis ``PMC<id>.<version>/`` mit ``.json`` (Metadaten
inklusive Lizenz), ``.xml`` (Volltext), ``.txt`` und ``.pdf``.

Ablauf:
1. Fuer einen PMCID die Version im Bucket auflisten.
2. Metadaten laden und die Lizenz pruefen (Standard: CC0, CC BY, CC BY-SA;
   keine NC- oder ND-Lizenzen).
3. XML laden und daraus Titel, Abstract, Abschnitte, Tabellen (Ueberschrift,
   Kopfzellen, Zeilen, Fussnoten) und Supplementary-Angaben als JSON ablegen.
4. Zustand fortschreiben, damit ein Abbruch ohne Doppelarbeit fortgesetzt wird.

Es wird nichts umgeschrieben: Zelltexte bleiben wie im XML, fehlende Angaben
bleiben leer.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any

BUCKET = "https://pmc-oa-opendata.s3.amazonaws.com"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "pmc_oa_cache"
OUT = HERE / "records" / "pmc_oa"
STATE = OUT / "state.jsonl"

ALLOWED_PREFIXES = ("CC0", "CC BY", "CC BY-SA", "CC BY 4.0", "CC BY-SA 4.0")


def license_allowed(license_text: str) -> bool:
    """Erlaubt nur Lizenzen ohne NC- und ND-Beschraenkung."""
    text = (license_text or "").strip()
    if not text:
        return False
    upper = text.upper()
    if "NC" in upper.replace("NONCOMMERCIAL", "NC") or "ND" in upper.replace("NODERIV", "ND"):
        return False
    return any(text.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def _get(url: str, timeout: int = 120) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def list_versions(pmcid: str) -> list[str]:
    """Liefert die vorhandenen Versionsschluessel eines PMCID, aufsteigend."""
    prefix = f"{pmcid}."
    query = urllib.parse.urlencode({"list-type": "2", "prefix": prefix, "max-keys": "50", "delimiter": "/"})
    payload = _get(f"{BUCKET}/?{query}").decode("utf-8", errors="replace")
    versions = sorted(set(re.findall(r"<Prefix>([^<]+)/</Prefix>", payload)))
    return [value for value in versions if value.startswith(prefix)]


def fetch_metadata(version_key: str) -> dict[str, Any]:
    name = version_key.split("/")[-1]
    return json.loads(_get(f"{BUCKET}/{version_key}/{name}.json").decode("utf-8", errors="replace"))


def fetch_xml(version_key: str) -> str:
    name = version_key.split("/")[-1]
    return _get(f"{BUCKET}/{version_key}/{name}.xml").decode("utf-8", errors="replace")


def parse_nxml(xml_text: str) -> dict[str, Any]:
    """Zerlegt ein PMC-NXML in Titel, Abstract, Abschnitte und Tabellen."""
    root = ET.fromstring(xml_text)
    article = root.find(".//article") if root.find(".//article") is not None else root

    def text_of(node: ET.Element | None) -> str:
        if node is None:
            return ""
        return "".join(node.itertext()).strip()

    title = text_of(article.find(".//title-group/article-title"))
    abstract = " ".join(text_of(node) for node in article.findall(".//abstract"))

    sections = []
    for sec in article.findall(".//body//sec"):
        heading = text_of(sec.find("title"))
        paragraphs = [text_of(p) for p in sec.findall("p")]
        if heading or paragraphs:
            sections.append({"heading": heading, "paragraphs": [p for p in paragraphs if p]})

    tables = []
    for table in article.findall(".//table-wrap"):
        head_rows = table.findall(".//thead/tr")
        head_ids = {id(tr) for tr in head_rows}
        header_rows = [[text_of(cell) for cell in tr.findall("th") + tr.findall("td")] for tr in head_rows]
        rows = []
        for tr in table.iter("tr"):
            if id(tr) in head_ids:
                continue
            cells = [text_of(cell) for cell in tr.findall("td") + tr.findall("th")]
            if cells:
                rows.append(cells)
        tables.append(
            {
                "label": text_of(table.find("label")),
                "caption": text_of(table.find("caption")),
                "header_rows": header_rows,
                "rows": rows,
                "footnotes": [text_of(fn) for fn in table.findall(".//table-wrap-foot//p")],
            }
        )

    supplementary = [
        {"label": text_of(node.find("label")), "caption": text_of(node.find("caption"))}
        for node in article.findall(".//supplementary-material")
    ]

    return {
        "title": title,
        "abstract": abstract,
        "sections": sections,
        "tables": tables,
        "supplementary": supplementary,
        "journal_meta": {
            "journal": text_of(article.find(".//journal-meta//journal-title")),
            "year": text_of(article.find(".//article-meta//pub-date/year")),
        },
    }


def done_ids() -> set[str]:
    if not STATE.exists():
        return set()
    ids = set()
    for line in STATE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            ids.add(json.loads(line)["article_id"])
        except (KeyError, json.JSONDecodeError):
            continue
    return ids


def process(pmcid: str, allow_nc: bool = False) -> dict[str, Any] | None:
    """Laedt und parst einen Artikel; gibt None zurueck, wenn er nicht zulaessig ist."""
    versions = list_versions(pmcid)
    if not versions:
        print(f"FEHLER {pmcid}: keine Version im Bucket")
        return None
    version_key = versions[-1]
    metadata = fetch_metadata(version_key)
    license_code = str(metadata.get("license_code") or "")
    if not (allow_nc or license_allowed(license_code)):
        print(f"uebersprungen {pmcid}: Lizenz {license_code!r} nicht zulaessig")
        return None
    parsed = parse_nxml(fetch_xml(version_key))
    return {
        "article_id": pmcid,
        "pmid": metadata.get("pmid"),
        "doi": metadata.get("doi"),
        "license": license_code,
        "source_file": f"{BUCKET}/{version_key}/",
        "retrieved": date.today().isoformat(),
        **parsed,
    }


def run(pmcids: list[str], limit: int, sleep: float, allow_nc: bool = False) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    done = done_ids()
    written = 0
    for pmcid in pmcids:
        if written >= limit:
            break
        if pmcid in done:
            continue
        try:
            record = process(pmcid, allow_nc=allow_nc)
        except Exception as error:  # noqa: BLE001 - Netzfehler werden protokolliert, nicht verschluckt
            print(f"FEHLER {pmcid}: {error}")
            continue
        if record is None:
            continue
        target = OUT / f"{pmcid}.json"
        target.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        with STATE.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"article_id": pmcid, "tables": len(record["tables"])}) + "\n")
        written += 1
        print(f"{pmcid}: {len(record['tables'])} Tabellen, {len(record['supplementary'])} Supplementary, Lizenz {record['license']}")
        time.sleep(sleep)
    print(f"fertig: {written} neue Artikel")
    return 0


def read_pmcids(path: Path) -> list[str]:
    values = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value:
            continue
        values.append(value if value.upper().startswith("PMC") else f"PMC{value}")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pmcid", action="append", default=[], help="einzelner PMCID, mehrfach moeglich")
    parser.add_argument("--pmcids-file", type=Path, default=None, help="Datei mit einem PMCID je Zeile")
    parser.add_argument("--limit", type=int, default=5, help="maximale Anzahl neuer Artikel")
    parser.add_argument("--sleep", type=float, default=1.0, help="Pause zwischen Artikeln in Sekunden")
    parser.add_argument("--allow-nc", action="store_true", help="auch NC-Lizenzen laden (nicht empfohlen)")
    parser.add_argument("--list-only", action="store_true", help="nur Service-Info ausgeben")
    args = parser.parse_args()

    if args.list_only:
        payload = _get(f"{BUCKET}/?list-type=2&max-keys=3").decode("utf-8", errors="replace")
        print(f"Bucket erreichbar: {BUCKET}, Beispiele: {re.findall(r'<Key>([^<]+)</Key>', payload)[:3]}")
        return 0

    pmcids = list(args.pmcid)
    if args.pmcids_file:
        pmcids.extend(read_pmcids(args.pmcids_file))
    if not pmcids:
        parser.error("mindestens --pmcid oder --pmcids-file angeben")
    return run(pmcids, args.limit, args.sleep, args.allow_nc)


if __name__ == "__main__":
    raise SystemExit(main())
