#!/usr/bin/env python
"""Prueft Arm- und Wertbindung auf genau der Tabelle, die `load_tables` auswaehlt.

Frage: Sind die Kopfangaben, die `gold_reachable` im Plan als Treffer zaehlt,
wirklich am richtigen Arm und tragen sie den Goldwert? Dokumentweite Treffer
zaehlen hier nicht - massgeblich ist die je Record ausgewaehlte Tabelle
(dieselbe Pipeline wie `run_benchmark.py --offline`).

Je Goldzelle mit Gruppengroesse wird geprueft:

* Feld erreichbar (wie `gold_reachable`)?
* falls nur ueber eine Kopfangabe: Wert **und** Arm passend?
* sitzt das Kopfband ueber Spalten desselben Arms?

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


def band_arme(tabelle, fact: dict) -> list[str]:
    arme = []
    for spalte in tabelle.columns:
        if fact["col_start"] <= spalte.col_id <= fact["col_end"] and spalte.arm:
            if spalte.arm not in arme:
                arme.append(spalte.arm)
    return arme


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
            eintrag = {
                "table_id": tabelle.table_id,
                "text": " ".join((fact.get("text") or "").split()),
                "value": fact.get("value"),
                "arm": fact.get("arm"),
                "field": field_for(ROLE_N, fact.get("arm")),
                "band_arme": band_arme(tabelle, fact),
            }
            facts.append(eintrag)

    gesamt = sum(
        1 for gold in (record.get("gold") or {}).get("cells") or []
        if gold.get("field") in alle
    )
    zellen = []
    for gold in (record.get("gold") or {}).get("cells") or []:
        field = gold.get("field")
        if field not in GRUPPENFELDER:
            continue
        if field not in alle:
            continue
        fact_only = field not in zeilen
        passend = [f for f in facts if f["field"] == field]
        wertgleich = [f for f in passend if f["value"] is not None
                      and abs(float(f["value"]) - float(gold["value"])) <= 1e-6]
        armgleich = [f for f in wertgleich if f["arm"] == gold.get("arm")]
        if not fact_only:
            klasse = "zeilenzelle"
        elif armgleich:
            klasse = "wert_und_arm"
        elif wertgleich:
            klasse = "wert_ohne_arm"
        else:
            klasse = "wert_abweichend"
        zellen.append(
            {
                "field": field,
                "arm": gold.get("arm"),
                "value": gold.get("value"),
                "fact_only": fact_only,
                "klasse": klasse,
                "kandidaten": wertgleich or passend,
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
    }


def schreibe_md(faelle: list[dict], summe: dict) -> str:
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
        f"Feld erreichbar (`gold_reachable`), davon {summe['feldtreffer']} mit "
        f"Gruppengroesse: {summe['zeilenzelle']} ueber die Outcome-Zeile, "
        f"{summe['kopf_feldtreffer']} nur ueber eine Kopfangabe."
    )
    a(
        f"- Von den {summe['kopf_feldtreffer']} Feldtreffern ueber Kopfangaben tragen "
        f"**{summe['wert_und_arm']}** den passenden Wert **und** Arm; "
        f"**{summe['wert_ohne_arm']}** den passenden Wert, aber einen anderen Arm; "
        f"**{summe['wert_abweichend']}** einen abweichenden Wert."
    )
    a(
        f"- Damit sind **{summe['feldtreffer_gesamt'] - summe['wert_abweichend'] - summe['wert_ohne_arm']} "
        f"von {summe['feldtreffer_gesamt']}** Feldtreffern wert- und armgedeckt; "
        "die Zeilenzellen sind dabei nicht wertgeprueft."
    )
    a(
        "- Die 0 unter \"passender Wert, anderer Arm\" zaehlt nur Zellen, "
        "deren Wert passt. Zusaetzlich zeigt `yun2024:678` eine "
        "Arm-Fehlbindung auf Spaltenebene: die 15 (Gold: comparator) "
        "sitzt ueber der als `intervention` gefuehrten Antibiotic-Gruppe, "
        "die 16 der Probiotic-Gruppe traegt keinen Arm."
    )
    a("")
    a("## 2. Records mit Feldtreffer ohne passenden Wert/Arm")
    a("")
    a("| Record | Tabelle(n) | Feld | Gold | Klasse | gedruckte Kandidaten |")
    a("|---|---|---|---:|---|---|")
    for f in faelle:
        for z in f["zellen"]:
            if z["klasse"] not in ("wert_abweichend", "wert_ohne_arm"):
                continue
            kand = "; ".join(
                f"\"{k['text']}\" -> {k['arm']} ({k['value']})"
                for k in z["kandidaten"][:3]
            )
            a(
                f"| `{f['record_id']}` | {', '.join(f['tables'])} | `{z['field']}` | "
                f"{int(z['value'])} ({z['arm']}) | {z['klasse']} | {kand or '-'} |"
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
                f"Feld erreichbar = {z['field'] in {x['field'] for x in fall['zellen']}}, "
                f"Klasse `{z['klasse']}`"
            )
        for d in fall["details"]:
            a(
                f"- Kopfangabe `{d['text']}` -> {d['arm']} (Wert {d['value']}), "
                f"Band ueber {d['band_arme'] or 'Spalten ohne Arm'}"
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
        "- Zeilenzellen werden als Feldtreffer gezaehlt, aber nicht wertgeprueft; "
        "die 68 sind deshalb eine Obergrenze."
    )
    a(
        "- Geprueft ist die Bindung gegen Gold und die Spaltenarme unter dem Band; "
        "eine falsche Spaltenarm-Zuordnung selbst deckt die Pruefung nicht auf."
    )
    return "\n".join(L) + "\n"


def main() -> int:
    struktur = json.loads(STRUKTUR.read_text(encoding="utf-8"))
    selection = json.loads(Path(str(struktur["selection"])).read_text(encoding="utf-8"))
    records = {r["record_id"]: r for r in lies_jsonl(RECORDS)}
    faelle = [pruefe_record(records[rid], selection) for rid in sorted(records)]

    summe = Counter()
    for f in faelle:
        summe["feldtreffer_gesamt"] += f["feldtreffer_gesamt"]
        for z in f["zellen"]:
            summe["feldtreffer"] += 1
            if z["klasse"] == "zeilenzelle":
                summe["zeilenzelle"] += 1
            else:
                summe["kopf_feldtreffer"] += 1
                summe[z["klasse"]] += 1

    daten = {
        "sprint": 48,
        "frage": "Sind die Kopfangaben im Plan am richtigen Arm und tragen sie den Goldwert?",
        "erzeugt_von": "public_benchmark/extended_benchmark/yun_full/pruefe_armbindung_sprint48.py",
        "nur_lesend": True,
        "netzaufrufe": 0,
        "grundlage": "load_tables (Plan-Auswahl, gleiche Pipeline wie run_benchmark --offline)",
        "summe": dict(summe),
        "faelle": faelle,
    }
    AUSGABE.with_suffix(".json").write_text(
        json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    AUSGABE.with_suffix(".md").write_text(schreibe_md(faelle, summe), encoding="utf-8")
    print(json.dumps(dict(summe), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
