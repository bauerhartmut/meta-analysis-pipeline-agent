#!/usr/bin/env python
"""Prueft Arm- und Wertbindung auf genau der Tabelle, die `load_tables` auswaehlt.

Frage: Sind die Kopfangaben, die `gold_reachable` im Plan als Treffer zaehlt,
wirklich am richtigen Arm und tragen sie den Goldwert? Dokumentweite Treffer
zaehlen hier nicht - massgeblich ist die je Record ausgewaehlte Tabelle
(dieselbe Pipeline wie `run_benchmark.py --offline`).

Je Goldzelle mit Gruppengroesse wird geprueft:

* Feld erreichbar (wie `gold_reachable`)?
* falls nur ueber eine Kopfangabe: Wert **und** Arm passend?
* traegt die Kopfangabe den Wert des *anderen* Arms (Arm vertauscht)?
* sitzt das Kopfband ueber Spalten desselben Arms (ok/gemischt/falsch/ohne Arm)?

Am Ende wird die Summe gegen `gold_reachable` aus `structure.json` abgeglichen;
bei Abweichung bricht das Skript ab, statt ein still falsches Artefakt zu
schreiben.

Rein lesend: keine Netzaufrufe, keine Predictions, kein Gold wird geschrieben.

Aufruf:
    .venv/bin/python public_benchmark/extended_benchmark/yun_full/pruefe_armbindung_sprint48.py
"""

from __future__ import annotations

import json
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

from extended_benchmark.table_decomposition.run_benchmark import (  # noqa: E402
    context_of,
    load_tables,
)
from research_agent.table_decomposition.semantics import (  # noqa: E402
    ROLE_N,
    field_for,
    reachable_cells,
)

STRUKTUR = BENCH / "analysis" / "table_decomposition_20261118" / "offline_struktur_20261118b" / "structure.json"
RECORDS = HIER / "records" / "yun699.jsonl"
AUSGABE = BENCH / "iterativ" / "ergebnisse" / "sprint48_armbindung_20261119"
GRUPPENFELDER = ("intervention_group_size", "comparator_group_size")


def lies_jsonl(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def band_pruefung(tabelle, fact: dict) -> dict[str, Any]:
    """Vergleicht die Spaltenarme unter dem Kopfband mit dem Arm der Angabe."""
    arme: list[str] = []
    for spalte in tabelle.columns:
        if fact["col_start"] <= spalte.col_id <= fact["col_end"] and spalte.arm:
            if spalte.arm not in arme:
                arme.append(spalte.arm)
    arm = fact.get("arm")
    if not arme:
        status = "ohne_arm"
    elif set(arme) == {arm}:
        status = "ok"
    elif arm in arme:
        status = "gemischt"
    else:
        status = "falsch"
    return {"arme": arme, "status": status}


def pruefe_record(record: dict, selection: dict) -> dict[str, Any]:
    entries = [e for e in selection.get("tables") or []
               if record["record_id"] in (e.get("record_ids") or [])]
    tables, _text, *_rest = load_tables(entries, record)
    context = context_of(record)

    zeilen: set = set()
    alle: set = set()
    facts: list[dict] = []
    details: list[dict] = []
    for tabelle in tables:
        zellen = reachable_cells(tabelle, context)
        zeilen |= {name for zeile, name in zellen if zeile >= 0}
        alle |= {name for _zeile, name in zellen}
        for fact in tabelle.header_facts:
            if not fact.get("arm"):
                continue
            band = band_pruefung(tabelle, fact)
            eintrag = {
                "table_id": tabelle.table_id,
                "text": " ".join((fact.get("text") or "").split()),
                "value": fact.get("value"),
                "arm": fact.get("arm"),
                "field": field_for(ROLE_N, fact.get("arm")),
                "band_arme": band["arme"],
                "band_status": band["status"],
            }
            facts.append(eintrag)

    gesamt = sum(
        1 for gold in (record.get("gold") or {}).get("cells") or []
        if gold.get("field") in alle
    )
    gold_werte = {
        gold.get("arm"): gold.get("value")
        for gold in (record.get("gold") or {}).get("cells") or []
        if gold.get("field") in GRUPPENFELDER
    }
    zellen = []
    for gold in (record.get("gold") or {}).get("cells") or []:
        field = gold.get("field")
        if field not in GRUPPENFELDER:
            continue
        if field not in alle:
            continue
        arm = gold.get("arm")
        other_arm = "comparator" if arm == "intervention" else "intervention"
        fact_only = field not in zeilen
        passend = [f for f in facts if f["field"] == field]
        wertgleich = [f for f in passend if f["value"] is not None
                      and abs(float(f["value"]) - float(gold["value"])) <= 1e-6]
        armgleich = [f for f in wertgleich if f["arm"] == arm]
        fremdwert = gold_werte.get(other_arm)
        vertauscht = [f for f in passend if f["value"] is not None
                      and fremdwert is not None
                      and abs(float(f["value"]) - float(fremdwert)) <= 1e-6]
        if not fact_only:
            klasse = "zeilenzelle"
        elif armgleich:
            klasse = "wert_und_arm"
        elif vertauscht:
            klasse = "arm_vertauscht"
        else:
            klasse = "wert_abweichend"
        zellen.append(
            {
                "field": field,
                "arm": arm,
                "value": gold.get("value"),
                "fact_only": fact_only,
                "klasse": klasse,
                "band_status": sorted({f["band_status"] for f in passend}),
                "kandidaten": armgleich or vertauscht or passend,
            }
        )
    for zelle in zellen:
        for fact in zelle["kandidaten"][:2]:
            details.append({
                "record_id": record["record_id"],
                "field": zelle["field"],
                "gold_value": zelle["value"],
                "gold_arm": zelle["arm"],
                "klasse": zelle["klasse"],
                **fact,
            })
    return {
        "record_id": record["record_id"],
        "tables": [t.table_id for t in tables],
        "feldtreffer_gesamt": gesamt,
        "zellen": zellen,
        "details": details,
        "band_status": [f["band_status"] for f in facts],
    }


def schreibe_md(faelle: list[dict], summe: dict, soll: int) -> str:
    L: list[str] = []
    a = L.append
    a("# Sprint 48: Arm- und Wertpruefung auf der Plan-Auswahl")
    a("")
    a(
        "Massgeblich ist die Tabelle, die `load_tables` je Record auswaehlt "
        "(dieselbe Pipeline wie `run_benchmark.py --offline`), nicht das ganze "
        "Dokument. Rein lesend: keine Netzaufrufe, keine Predictions geschrieben."
    )
    a("")
    a("## 1. Befund")
    a("")
    a(
        f"- **{summe['feldtreffer_gesamt']} Goldzellen** sind im Plan ueber ihr "
        f"Feld erreichbar (`gold_reachable`, Sollwert {soll}); davon "
        f"{summe['feldtreffer']} mit Gruppengroesse: {summe['zeilenzelle']} "
        f"ueber die Outcome-Zeile, {summe['kopf_feldtreffer']} nur ueber eine "
        "Kopfangabe."
    )
    a(
        f"- Von den {summe['kopf_feldtreffer']} Feldtreffern ueber Kopfangaben "
        f"tragen **{summe['wert_und_arm']}** Wert **und** Arm, "
        f"**{summe['arm_vertauscht']}** tragen den Wert des anderen Arms "
        f"(Arm vertauscht), **{summe['wert_abweichend']}** einen anderen Wert."
    )
    a(
        f"- Damit sind **{summe['feldtreffer_gesamt'] - summe['arm_vertauscht'] - summe['wert_abweichend']} "
        f"von {summe['feldtreffer_gesamt']}** Feldtreffern nicht durch eine "
        "wertabweichende Kopfangabe widerlegt. Das ist eine **Obergrenze**: "
        "Zeilenzellen und Messwertzellen sind nicht wertgeprueft, und "
        "verifiziert ist nur der Abgleich gegen Gold, nicht die Spaltenarm-"
        "Zuordnung selbst."
    )
    a(
        f"- Bandpruefung aller {summe['band_ok'] + summe['band_gemischt'] + summe['band_falsch'] + summe['band_ohne_arm']} "
        f"Kopfangaben der Plan-Tabellen: {summe['band_ok']} ok, "
        f"{summe['band_gemischt']} gemischt, {summe['band_falsch']} falsch, "
        f"{summe['band_ohne_arm']} ohne Arm. "
        "Ein Band ueber gemischten oder fremden Armen wird als Befund "
        "ausgewiesen, aendert die Wertzaehlung aber nicht."
    )
    a(
        f"- Abgleich: Summe {summe['feldtreffer_gesamt']} = Sollwert {soll} "
        "aus `structure.json`."
    )
    a("")
    a("## 2. Records mit Feldtreffer ohne passenden Wert/Arm")
    a("")
    a("| Record | Tabelle(n) | Feld | Gold | Klasse | Band | gedruckte Kandidaten |")
    a("|---|---|---|---:|---|---|---|")
    for f in faelle:
        for z in f["zellen"]:
            if z["klasse"] not in ("wert_abweichend", "arm_vertauscht"):
                continue
            kand = "; ".join(
                f"\"{k['text']}\" -> {k['arm']} ({k['value']})"
                for k in z["kandidaten"][:3]
            )
            a(
                f"| `{f['record_id']}` | {', '.join(f['tables'])} | `{z['field']}` | "
                f"{int(z['value'])} ({z['arm']}) | {z['klasse']} | "
                f"{', '.join(z['band_status']) or '-'} | {kand or '-'} |"
            )
    a("")
    a("## 3. Der Fall yun2024:678")
    a("")
    fall = next((f for f in faelle if f["record_id"] == "yun2024:678"), None)
    if fall:
        a(f"- Plan-Tabelle: `{', '.join(fall['tables'])}`")
        for z in fall["zellen"]:
            a(
                f"- Gold `{z['field']}` = {int(z['value'])} ({z['arm']}): "
                f"Klasse `{z['klasse']}`, Band `{', '.join(z['band_status']) or '-'}`"
            )
        for d in fall["details"]:
            a(
                f"- Kopfangabe `{d['text']}` -> {d['arm']} (Wert {d['value']}), "
                f"Band ueber {d['band_arme'] or 'Spalten ohne Arm'} "
                f"({d['band_status']})"
            )
        a("")
        a(
            "Die Tabelle bindet `n = 15` an **intervention**, Gold verlangt "
            "16/intervention und 15/comparator. Die 15 steht ueber der "
            "Antibiotic-Gruppe (Spalten 6-10), die der Plan als intervention "
            "fuehrt; die 16 der Probiotic-Gruppe traegt keinen Arm. Der "
            "Planwert 1 ist damit ein Feldtreffer ohne passenden Wert - und "
            "am falschen Arm; wertgeprueft bleibt 0."
        )
    else:
        a("Nicht in der Auswahl.")
    a("")
    a("## 4. Grenzen")
    a("")
    a(
        "- Zeilenzellen und Messwerte werden als Feldtreffer gezaehlt, aber "
        "nicht wertgeprueft; die Zahl der nicht widerlegten Feldtreffer ist "
        "deshalb eine Obergrenze."
    )
    a(
        "- Die Bandpruefung nutzt die Spaltenarme des Plans. Eine bereits dort "
        "falsche Zuordnung (426) erkennt sie nicht; sie findet nur Baender, "
        "die ueber gemischten oder fremden Armen sitzen."
    )
    a(
        "- `arm_vertauscht` prueft, ob eine Kopfangabe den Goldwert des "
        "anderen Arms traegt; sie erkennt keine Vertauschung, deren Wert in "
        "der Tabelle gar nicht vorkommt."
    )
    return "\n".join(L) + "\n"


def main() -> int:
    struktur = json.loads(STRUKTUR.read_text(encoding="utf-8"))
    soll = int(struktur["strategy_summary"]["A"]["gold_reachable"])
    selection = json.loads(Path(str(struktur["selection"])).read_text(encoding="utf-8"))
    records = {r["record_id"]: r for r in lies_jsonl(RECORDS)}
    faelle = [pruefe_record(records[rid], selection) for rid in sorted(records)]

    summe = Counter()
    for f in faelle:
        summe["feldtreffer_gesamt"] += f["feldtreffer_gesamt"]
        for s in f["band_status"]:
            summe["band_" + s] += 1
        for z in f["zellen"]:
            summe["feldtreffer"] += 1
            if z["klasse"] == "zeilenzelle":
                summe["zeilenzelle"] += 1
            else:
                summe["kopf_feldtreffer"] += 1
                summe[z["klasse"]] += 1

    if summe["feldtreffer_gesamt"] != soll:
        raise SystemExit(
            f"Abgleich fehlgeschlagen: Skript {summe['feldtreffer_gesamt']} != "
            f"structure.json {soll}. structure.json neu erzeugt?"
        )

    daten = {
        "sprint": 48,
        "frage": "Sind die Kopfangaben im Plan am richtigen Arm und tragen sie den Goldwert?",
        "erzeugt_von": "public_benchmark/extended_benchmark/yun_full/pruefe_armbindung_sprint48.py",
        "nur_lesend": True,
        "netzaufrufe": 0,
        "grundlage": "load_tables (Plan-Auswahl, gleiche Pipeline wie run_benchmark --offline)",
        "abgleich": {"feldtreffer_gesamt": summe["feldtreffer_gesamt"], "gold_reachable": soll, "ok": True},
        "summe": dict(summe),
        "faelle": faelle,
    }
    AUSGABE.with_suffix(".json").write_text(
        json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    AUSGABE.with_suffix(".md").write_text(schreibe_md(faelle, summe, soll), encoding="utf-8")
    print(json.dumps(dict(summe), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
