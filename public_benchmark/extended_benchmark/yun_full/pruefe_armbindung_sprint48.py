#!/usr/bin/env python
"""Prueft die neu gezaehlten Kopfangaben der 23 Records mit geaenderter Reichweite.

Frage: Gehoeren die seit Sprint 44 mitgezaehlten `n = ...`-Kopfangaben wirklich
zum richtigen Arm, und tragen sie den Goldwert - oder zaehlt `gold_reachable`
nur das Feld und ignoriert Wert und Arm?

Verglichen wird der neue Strukturlauf (`offline_struktur_20261118b/structure.json`)
mit dem Stand vor der Neuerzeugung (`git show 911e593^:...`). Je neu erreichter
Goldzelle werden die tragenden Kopfangaben geprueft:

* Wert: `fact.value == gold.value`
* Arm: `fact.arm == gold.arm`
* Band: liegen die Spalten unter dem Kopfband auf demselben Arm?

Rein lesend: keine Netzaufrufe, keine Predictions, kein Gold wird geschrieben.

Aufruf:
    .venv/bin/python public_benchmark/extended_benchmark/yun_full/pruefe_armbindung_sprint48.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent
ROOT = HIER.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BENCH.parent))
sys.path.insert(0, str(BENCH))

from research_agent.table_decomposition.parser import parse_document  # noqa: E402
from research_agent.table_decomposition.semantics import (  # noqa: E402
    ROLE_N,
    enrich_table,
    field_for,
    reachable_cells,
)

STRUKTUR = BENCH / "analysis" / "table_decomposition_20261118" / "offline_struktur_20261118b" / "structure.json"
ALT_REV = "911e593^"
RECORDS = HIER / "records" / "yun699.jsonl"
AUSGABE = BENCH / "iterativ" / "ergebnisse" / "sprint48_armbindung_20261119"
GRUPPENFELDER = ("intervention_group_size", "comparator_group_size")


def lies_jsonl(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def alte_werte() -> dict[str, int]:
    relativ = STRUKTUR.relative_to(ROOT).as_posix()
    roh = subprocess.run(
        ["git", "show", f"{ALT_REV}:{relativ}"],
        capture_output=True, text=True, check=True,
    ).stdout
    daten = json.loads(roh)
    return {e["record_id"]: e["gold_reachable"] for e in daten["records"]["A"]}


def kontext(record: dict) -> dict[str, Any]:
    ctx = record.get("context") or {}
    return {
        "intervention": ctx.get("intervention"),
        "comparator": ctx.get("comparator"),
        "outcome": ctx.get("outcome"),
        "outcome_type": ctx.get("outcome_type"),
        "timepoint_target": (record.get("timepoint") or {}).get("target"),
    }


def gleicher_wert(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) <= 1e-6


def band_arme(tabelle, fact: dict) -> list[str]:
    """Arme der Spalten unter dem Kopfband (ohne Wiederholung)."""
    arme = []
    for spalte in tabelle.columns:
        if fact["col_start"] <= spalte.col_id <= fact["col_end"] and spalte.arm:
            if spalte.arm not in arme:
                arme.append(spalte.arm)
    return arme


def pruefe_record(record: dict, text: str) -> dict[str, Any]:
    ctx = kontext(record)
    doc_id = str((record.get("document") or {}).get("id"))
    parsed = parse_document(text, doc_id)
    for tabelle in parsed.tables:
        enrich_table(tabelle, ctx)

    zeilen_felder: set = set()
    alle_felder: set = set()
    facts: list[dict] = []
    for tabelle in parsed.tables:
        zellen = reachable_cells(tabelle, ctx)
        zeilen_felder |= {name for zeile, name in zellen if zeile >= 0}
        alle_felder |= {name for _zeile, name in zellen}
        for fact in tabelle.header_facts:
            if not fact.get("arm"):
                continue
            facts.append(
                {
                    "table_id": tabelle.table_id,
                    "text": " ".join((fact.get("text") or "").split()),
                    "value": fact.get("value"),
                    "arm": fact.get("arm"),
                    "arm_basis": fact.get("arm_basis"),
                    "field": field_for(ROLE_N, fact.get("arm")),
                    "band_arme": band_arme(tabelle, fact),
                }
            )

    zellen = []
    for gold in (record.get("gold") or {}).get("cells") or []:
        if gold.get("field") not in GRUPPENFELDER:
            continue
        neu_gezaehlt = gold["field"] in alle_felder and gold["field"] not in zeilen_felder
        passend = [f for f in facts if f["field"] == gold["field"]]
        wertgleich = [f for f in passend if f["value"] is not None and gleicher_wert(f["value"], gold["value"])]
        armgleich = [f for f in wertgleich if f["arm"] == gold.get("arm")]
        if not neu_gezaehlt:
            klasse = "nicht_ueber_kopf"
        elif armgleich:
            klasse = "wert_und_arm_stimmig"
        elif wertgleich:
            klasse = "wert_stimmig_arm_falsch"
        elif passend:
            klasse = "feld_belegt_wert_abweichend"
        else:
            klasse = "feld_ohne_beleg"
        zellen.append(
            {
                "field": gold["field"],
                "arm": gold.get("arm"),
                "value": gold.get("value"),
                "neu_gezaehlt": neu_gezaehlt,
                "klasse": klasse,
                "passende_facts": passend,
                "wertgleiche_facts": wertgleich,
            }
        )
    return {"record_id": record["record_id"], "dokument_id": doc_id, "zellen": zellen}


def schreibe_md(faelle: list[dict], summe: dict, aenderung: list[tuple]) -> str:
    L: list[str] = []
    a = L.append
    a("# Sprint 48: Arm- und Wertpruefung der neu gezaehlten Kopfangaben")
    a("")
    a(
        f"Stichprobe: alle **{len(faelle)}** Records, deren `gold_reachable` sich "
        "durch die Neuerzeugung geaendert hat (Vergleich gegen `911e593^`). "
        "Rein lesend: keine Netzaufrufe, keine Predictions geschrieben."
    )
    a("")
    a("## 1. Befund")
    a("")
    a(
        f"- **{summe['neu_gezaehlt']} Goldzellen** sind neu ueber Kopfangaben "
        f"erreichbar; {summe['wert_und_arm_stimmig']} davon mit **passendem Wert "
        f"und Arm**, {summe['wert_stimmig_arm_falsch']} mit passendem Wert aber "
        f"falschem Arm."
    )
    a(
        f"- **{summe['feld_belegt_wert_abweichend']} Zellen** werden nur deshalb "
        "gezaehlt, weil das *Feld* von einer Kopfangabe belegt ist - der gedruckte "
        "Wert weicht vom Goldwert ab (Untergruppen statt Gesamtgruppe)."
    )
    a(
        f"- Bandpruefung: {summe['band_konkordant']} tragende Angaben sitzen ueber "
        f"Spalten desselben Arms, {summe['band_diskordant']} ueber Spalten eines "
        f"anderen Arms, {summe['band_ohne_arm']} ueber Spalten ohne Arm."
    )
    a("")
    a("## 2. Je Record")
    a("")
    a("| Record | alt -> neu | neu ueber Kopf | Wert+Arm | Wert ok, Arm falsch | Wert abweichend |")
    a("|---|---:|---:|---:|---:|---:|")
    for f in faelle:
        neu = [z for z in f["zellen"] if z["neu_gezaehlt"]]
        alt, jetzt = f["alt"], f["neu"]
        a(
            f"| `{f['record_id']}` | {alt} -> {jetzt} | {len(neu)} | "
            f"{sum(1 for z in neu if z['klasse'] == 'wert_und_arm_stimmig')} | "
            f"{sum(1 for z in neu if z['klasse'] == 'wert_stimmig_arm_falsch')} | "
            f"{sum(1 for z in neu if z['klasse'] == 'feld_belegt_wert_abweichend')} |"
        )
    a("")
    a("## 3. Beispiele")
    a("")
    for f in faelle:
        beispiele = [z for z in f["zellen"] if z["neu_gezaehlt"]][:2]
        for z in beispiele:
            belege = "; ".join(
                f"{b['table_id']}: \"{b['text']}\" -> {b['arm']} (Band ueber {b['band_arme'] or 'ohne Arm'})"
                for b in z["passende_facts"][:2]
            )
            a(
                f"- `{f['record_id']}` {z['field']}={int(z['value'])}: {z['klasse']}"
                + (f" - {belege}" if belege else "")
            )
    a("")
    a("## 4. Grenzen")
    a("")
    a(
        "- Geprueft ist die Bindung des Parsers gegen die Spaltenarme unter dem "
        "Band; eine falsche Spaltenarm-Zuordnung selbst wird nicht aufgedeckt."
    )
    a(
        "- `gold_reachable` zaehlt Felder, nicht Werte. Die Zaehlung kann daher "
        "Felder als erreichbar fuehren, obwohl der gedruckte Wert ein anderer ist."
    )
    return "\n".join(L) + "\n"


def main() -> int:
    alt = alte_werte()
    neu_daten = json.loads(STRUKTUR.read_text(encoding="utf-8"))
    neu = {e["record_id"]: e["gold_reachable"] for e in neu_daten["records"]["A"]}
    geaendert = [(rid, alt[rid], neu[rid]) for rid in alt if alt[rid] != neu[rid]]
    records = {r["record_id"]: r for r in lies_jsonl(RECORDS)}

    faelle = []
    for rid, alt_wert, neu_wert in sorted(geaendert, key=lambda x: (-(x[2] - x[1]), x[0])):
        record = records[rid]
        text = (ROOT / (record.get("document") or {}).get("path", "")).read_text(
            encoding="utf-8", errors="replace"
        )
        fall = pruefe_record(record, text)
        fall["alt"] = alt_wert
        fall["neu"] = neu_wert
        faelle.append(fall)

    summe = Counter()
    band = Counter()
    for f in faelle:
        for z in f["zellen"]:
            if not z["neu_gezaehlt"]:
                continue
            summe["neu_gezaehlt"] += 1
            summe[z["klasse"]] += 1
            if z["klasse"] in ("wert_und_arm_stimmig", "wert_stimmig_arm_falsch"):
                for fact in z["wertgleiche_facts"]:
                    if fact["arm"] == z["arm"]:
                        band["konkordant" if z["arm"] in fact["band_arme"] else (
                            "diskordant" if fact["band_arme"] else "ohne_arm"
                        )] += 1
    summe.update({
        "band_konkordant": band["konkordant"],
        "band_diskordant": band["diskordant"],
        "band_ohne_arm": band["ohne_arm"],
    })

    daten = {
        "sprint": 48,
        "frage": "Gehoeren die neu gezaehlten Kopfangaben zum richtigen Arm und tragen sie den Goldwert?",
        "erzeugt_von": "public_benchmark/extended_benchmark/yun_full/pruefe_armbindung_sprint48.py",
        "nur_lesend": True,
        "netzaufrufe": 0,
        "vergleich": ALT_REV,
        "records": len(faelle),
        "summe": dict(summe),
        "aenderung": [{"record_id": r, "alt": a, "neu": n} for r, a, n in geaendert],
        "faelle": faelle,
    }
    AUSGABE.with_suffix(".json").write_text(
        json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    AUSGABE.with_suffix(".md").write_text(schreibe_md(faelle, summe, geaendert), encoding="utf-8")
    print(json.dumps({"records": len(faelle), **dict(summe)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
