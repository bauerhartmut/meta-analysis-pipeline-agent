#!/usr/bin/env python
"""Gemeinsame Bausteine fuer die iterative Extraktion.

Enthaelt nur Lese- und Hilfsfunktionen: Record- und Predictions-Zugriff,
Zerlegung eines Auszugs in Text-, Tabellen- und Abbildungsbloecke, Suche nach
einem Zahlenwert und Zugriff auf den Volltext-XML. Es wird nichts geschrieben
und nichts an bestehenden Laeufen veraendert.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
REPO = BENCH.parent.parent
RECORDS = BENCH / "yun_full" / "records" / "yun699.jsonl"
VORLAUF = BENCH / "runs" / "yun699_8000_alle_20261117" / "predictions.jsonl"
XML_DIR = (
    REPO
    / "public_benchmark"
    / "raw_data"
    / "yun_llm_meta_analysis"
    / "evaluation"
    / "data"
    / "no_attributes_xml_files"
)

FELDER = (
    "intervention_group_size",
    "intervention_events",
    "intervention_mean",
    "intervention_standard_deviation",
    "comparator_group_size",
    "comparator_events",
    "comparator_mean",
    "comparator_standard_deviation",
)

# Synonyme fuer die Feldsuche im Text. Bewusst breit: die Suche soll Textstellen
# vorschlagen, nicht entscheiden.
FELD_BEGRIFFE = {
    "group_size": ("patients", "participants", "subjects", "n =", "randomised", "randomized", "analysed", "analyzed"),
    "events": ("events", "cases", "incidence", "occurred", "number of"),
    "mean": ("mean", "average", "change", "score"),
    "standard_deviation": ("sd", "standard deviation", "±", "plus-minus"),
}


def lies(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def lade_records() -> dict[str, dict]:
    return {r["record_id"]: r for r in lies(RECORDS)}


def lade_modell(zeilen: list[dict], modell: str = "glm") -> dict[str, dict]:
    """Letzte Zeile je Record; der Lauf kann durch Neustarts mehrere haben."""
    out: dict[str, dict] = {}
    for zeile in zeilen:
        if zeile.get("model") != modell:
            continue
        out[zeile["record_id"]] = zeile
    return out


def gold_werte(record: dict) -> dict[str, float]:
    werte: dict[str, float] = {}
    for zelle in record["gold"]["cells"]:
        werte.setdefault(zelle["field"], zelle["value"])
    return werte


def gold_roh(record: dict) -> dict[str, str]:
    roh: dict[str, str] = {}
    for zelle in record["gold"]["cells"]:
        roh.setdefault(zelle["field"], str(zelle.get("raw") or zelle["value"]))
    return roh


def modell_werte(zeile: dict) -> dict[str, float]:
    werte: dict[str, float] = {}
    for zelle in zeile.get("rows") or []:
        werte.setdefault(zelle["field"], zelle["value"])
    return werte


def dokument(record: dict) -> str:
    pfad = REPO / record["document"]["path"]
    if not pfad.exists():
        return ""
    return pfad.read_text(encoding="utf-8", errors="replace")


def volltext(record: dict) -> str:
    """Volltext-XML als Klartext; leer, wenn keine Datei vorliegt."""
    pmcid = str(record["document"]["id"]).strip()
    pfad = XML_DIR / f"{pmcid}.xml"
    if not pfad.exists():
        return ""
    roh = pfad.read_text(encoding="utf-8", errors="replace")
    roh = re.sub(r"(?is)<(script|style).*?</\1>", " ", roh)
    roh = re.sub(r"(?s)<[^>]+>", " ", roh)
    return re.sub(r"\s+", " ", html.unescape(roh)).strip()


# Der schliessende Trenner steht in diesem Korpus direkt hinter der letzten
# Tabellenzelle ("... 15 (2)::::  Table 4 presents ..."), also nicht am
# Zeilenanfang. Deshalb wird bis zum naechsten vierfachen Doppelpunkt gelesen.
TABELLE_RE = re.compile(r"(?s)::::table-wrap.{0,40000}?::::")
ABBILDUNG_RE = re.compile(r"(?im)^[ \t]*(?::::[ \t]*caption\b|figure[ \t]+\d+|fig\.[ \t]*\d+).*$")


def bloecke(text: str) -> list[dict]:
    """Zerlegt den Auszug in Bloecke mit exakten Zeichenpositionen.

    Typen: `tabelle` (innerhalb von ::::table-wrap), `abbildung` (Caption oder
    Figure-Verweis ausserhalb einer Tabelle), `text` (alles andere).
    Rueckgabe: `[{"typ", "start", "ende"}]`, nach Start sortiert und
    ueberlappungsfrei.
    """
    belegt: list[tuple[int, int, str]] = []
    for match in TABELLE_RE.finditer(text):
        belegt.append((match.start(), match.end(), "tabelle"))

    def in_tabelle(pos: int) -> bool:
        return any(start <= pos < ende for start, ende, _ in belegt)

    for match in ABBILDUNG_RE.finditer(text):
        if in_tabelle(match.start()):
            continue
        # Unterschrift endet an der naechsten Leerzeile, hoechstens 12 Zeilen.
        ende = match.end()
        for _ in range(12):
            naechste = text.find("\n", ende)
            if naechste < 0:
                break
            zeile = text[ende:naechste].strip()
            if not zeile:
                break
            ende = naechste
        belegt.append((match.start(), ende, "abbildung"))

    belegt.sort()
    ergebnis: list[dict] = []
    zeiger = 0
    for start, ende, typ in belegt:
        if start < zeiger:
            start = zeiger
        if start > zeiger:
            ergebnis.append({"typ": "text", "start": zeiger, "ende": start})
        if ende > start:
            ergebnis.append({"typ": typ, "start": start, "ende": ende})
        zeiger = max(zeiger, ende)
    if zeiger < len(text):
        ergebnis.append({"typ": "text", "start": zeiger, "ende": len(text)})
    return ergebnis


def als_zahl(text: str) -> float | None:
    """Liest eine Zahl mit Tausender- oder Dezimalkomma; `None` bei Unlesbarkeit."""
    s = (text or "").strip().replace(" ", "").replace("\u2212", "-")
    if not s:
        return None
    if re.fullmatch(r"-?\d{1,3}(,\d{3})+", s):
        s = s.replace(",", "")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    elif re.fullmatch(r"-?\d+,\d+", s):
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _varianten(raw: str) -> list[str]:
    """Schreibvarianten einer Goldzahl (Komma/Punkt, Tausender, .0)."""
    roh = (raw or "").strip()
    ohne_leer = roh.replace(" ", "")
    out = {roh, ohne_leer}
    zahl = als_zahl(ohne_leer)
    if zahl is not None:
        if re.fullmatch(r"-?\d+", ohne_leer):
            out.add(f"{ohne_leer}.0")
            if abs(zahl) >= 1000:
                out.add(f"{int(zahl):,}")
                out.add(f"{int(zahl)}")
        elif re.fullmatch(r"-?\d+,\d+", ohne_leer):
            out.add(ohne_leer.replace(",", "."))
        elif re.fullmatch(r"-?\d+\.\d+", ohne_leer):
            out.add(ohne_leer.replace(".", ","))
            if len(ohne_leer.split(".")[-1]) == 1:
                out.add(ohne_leer + "0")
            if ohne_leer.endswith("0"):
                out.add(ohne_leer[:-1])
        elif re.fullmatch(r"-?\d+\.0", ohne_leer):
            out.add(ohne_leer[:-2])
    return [v for v in out if v]


def finde_zahl(text: str, raw: str) -> list[int]:
    """Alle Positionen, an denen die Goldzahl als eigenstaendige Zahl steht."""
    treffer: list[int] = []
    for variante in _varianten(raw):
        muster = r"(?<![\d.,])" + re.escape(variante) + r"(?![\d])"
        for match in re.finditer(muster, text):
            treffer.append(match.start())
    return sorted(set(treffer))


def naehe(text: str, pos: int, begriffe: list[str], fenster: int = 220) -> bool:
    """Steht einer der Begriffe im Fenster um die Position?"""
    ausschnitt = text[max(0, pos - fenster) : pos + fenster].lower()
    return any(b.lower() in ausschnitt for b in begriffe if b)


def arm_begriffe(record: dict, arm: str) -> list[str]:
    kontext = record["context"]
    name = str(kontext.get("intervention" if arm == "intervention" else "comparator") or "")
    begriffe = [name]
    begriffe += [t for t in re.split(r"[()/,;]|\band\b", name) if len(t.strip()) > 3]
    return [b.strip() for b in begriffe if b.strip()]


def block_typ_an(bloecke_liste: list[dict], pos: int) -> str:
    for block in bloecke_liste:
        if block["start"] <= pos < block["ende"]:
            return block["typ"]
    return "text"
