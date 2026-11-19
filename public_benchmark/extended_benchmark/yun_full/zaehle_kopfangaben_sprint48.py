#!/usr/bin/env python
"""Zaehlt Kopfangaben unter den Goldzellen der 33 P5-Budgetfaelle (Sprint 48).

Frage: Wie viele Goldzellen der 33 `length_ohne_ergebnis`-Records stehen als
feste Kopfangabe (`n = ...`) in den Tabellen und sind damit fuer den
Tabellenpfad (Zellen der Outcome-Zeile) nicht erreichbar? Das entscheidet, ob
ein Kopf-Fakten-Prompt der richtige Hebel ist.

Rein lesend: keine Netzaufrufe, keine Predictions, kein Gold wird geschrieben.
Gelesen werden die P5-Predictions, die Records und die Markdown-Dokumente;
Kopfangaben kommen aus dem vorhandenen Parser und `enrich_table`
(`Table.header_facts`), nicht aus einer neuen Erkennung.

Aufruf:
    .venv/bin/python public_benchmark/extended_benchmark/yun_full/zaehle_kopfangaben_sprint48.py
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

from research_agent.table_decomposition.parser import ROLE_LABEL, parse_document  # noqa: E402
from research_agent.table_decomposition.semantics import (  # noqa: E402
    enrich_table,
    reachable_cells,
)

RUN_ID = "yun699_p5_24000_20261118"
RUN = BENCH / "runs" / RUN_ID / "predictions.jsonl"
RECORDS = HIER / "records" / "yun699.jsonl"
AUSGABE = BENCH / "iterativ" / "ergebnisse" / "sprint48_kopfangaben_20261119"

#: Felder, die eine Gruppengroesse tragen; nur sie koennen eine Kopfangabe sein.
GRUPPENFELDER = ("intervention_group_size", "comparator_group_size")


def lies_jsonl(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


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


def kopfangaben_je_dokument(text: str, doc_id: str, context: dict) -> list[dict]:
    """Alle festen Kopfangaben (`n = ...`) aller Tabellen eines Dokuments."""
    try:
        parsed = parse_document(text, doc_id)
    except Exception as fehler:  # noqa: BLE001 - Parserausfall ist ein Befund
        return [{"parser_fehler": f"{type(fehler).__name__}: {fehler}"}]
    facts: list[dict] = []
    for tabelle in parsed.tables:
        enrich_table(tabelle, context)
        for fact in tabelle.header_facts:
            facts.append(
                {
                    "table_id": tabelle.table_id,
                    "text": " ".join((fact.get("text") or "").split()),
                    "value": fact.get("value"),
                    "arm": fact.get("arm"),
                    "basis": fact.get("basis"),
                    "arm_basis": fact.get("arm_basis"),
                }
            )
    return facts


def zeilen_und_zellfelder(text: str, doc_id: str, context: dict) -> tuple[set, set]:
    """Felder, die die Outcome-Zeile hergibt, gegen alle erwartbaren Felder.

    `reachable_cells` enthaelt seit Sprint 44 auch Kopfangaben (Adresse
    ``(-1, feld)``). Fuer die Frage nach dem *Tabellenpfad* zaehlen hier nur
    Zellen mit einer echten Zeile; die Differenz sind die reinen Kopffelder.
    """
    try:
        parsed = parse_document(text, doc_id)
    except Exception:  # noqa: BLE001
        return set(), set()
    zeilen: set = set()
    alles: set = set()
    for tabelle in parsed.tables:
        enrich_table(tabelle, context)
        zellen = reachable_cells(tabelle, context)
        alles |= {name for _zeile, name in zellen}
        zeilen |= {name for zeile, name in zellen if zeile >= 0}
    return zeilen, alles


def klassifiziere(zelle: dict, facts: list[dict]) -> tuple[str, list[dict]]:
    """Wie steht diese Goldzelle im Dokument da?"""
    if zelle.get("field") not in GRUPPENFELDER:
        return "kein_gruppenfeld", []
    treffer = [
        f for f in facts
        if f.get("value") is not None and gleicher_wert(zelle["value"], f["value"])
    ]
    if not treffer:
        return "keine_kopfangabe", []
    arm = zelle.get("arm")
    with_arm = [f for f in treffer if f.get("arm") == arm]
    if with_arm:
        return "kopfangabe_mit_arm", with_arm
    without_arm = [f for f in treffer if not f.get("arm")]
    if without_arm:
        return "kopfangabe_ohne_arm", without_arm
    return "kopfangabe_anderer_arm", treffer


def zaehle_fall(row: dict, record: dict, text: str) -> dict[str, Any]:
    doc_id = str((record.get("document") or {}).get("id") or row["record_id"])
    context = kontext(record)
    facts = kopfangaben_je_dokument(text, doc_id, context)
    parser_fehler = next((f["parser_fehler"] for f in facts if "parser_fehler" in f), "")
    facts = [f for f in facts if "parser_fehler" not in f]
    zeilen_felder, _ = zeilen_und_zellfelder(text, doc_id, context)

    zellen = []
    for zelle in (record.get("gold") or {}).get("cells") or []:
        klasse, belege = klassifiziere(zelle, facts)
        ueber_zeile = zelle.get("field") in zeilen_felder
        # Nur eine Kopfangabe mit **diesem Wert** und belegtem Arm ist fuer die
        # Zelle ein Treffer. `reachable_cells` arbeitet feldweise und wuerde
        # etwa in `yun2024:252` die Felder als erreichbar fuehren, obwohl die
        # Tabelle `*n* = 398` druckt und Gold 402 verlangt.
        nur_kopf = klasse == "kopfangabe_mit_arm" and not ueber_zeile
        zellen.append(
            {
                "field": zelle.get("field"),
                "arm": zelle.get("arm"),
                "value": zelle.get("value"),
                "klasse": klasse,
                "belege": belege,
                "feld_ueber_outcome_zeile": ueber_zeile,
                "nur_als_kopfangabe": nur_kopf,
            }
        )

    return {
        "record_id": row["record_id"],
        "dokument_id": doc_id,
        "parser_fehler": parser_fehler,
        "gold_zellen": len(zellen),
        "gruppenfeld_zellen": sum(1 for z in zellen if z["field"] in GRUPPENFELDER),
        "kopfangabe_mit_arm": sum(1 for z in zellen if z["klasse"] == "kopfangabe_mit_arm"),
        "kopfangabe_ohne_arm": sum(1 for z in zellen if z["klasse"] == "kopfangabe_ohne_arm"),
        "kopfangabe_anderer_arm": sum(
            1 for z in zellen if z["klasse"] == "kopfangabe_anderer_arm"
        ),
        "keine_kopfangabe": sum(1 for z in zellen if z["klasse"] == "keine_kopfangabe"),
        "kein_gruppenfeld": sum(1 for z in zellen if z["klasse"] == "kein_gruppenfeld"),
        "ueber_outcome_zeile": sum(1 for z in zellen if z["feld_ueber_outcome_zeile"]),
        "nur_als_kopfangabe": sum(1 for z in zellen if z["nur_als_kopfangabe"]),
        "weder_noch": sum(
            1
            for z in zellen
            if not z["feld_ueber_outcome_zeile"] and not z["nur_als_kopfangabe"]
        ),
        "kopfangaben_im_dokument": len(facts),
        "kopfangaben_mit_arm": sum(1 for f in facts if f.get("arm")),
        "zellen": zellen,
    }


def de(wert: float) -> str:
    """Deutsche Dezimalschreibweise fuer die Anteile im Bericht."""
    return f"{wert:.1f}".replace(".", ",")


def schreibe_md(faelle: list[dict]) -> str:
    n = len(faelle)
    gold = sum(f["gold_zellen"] for f in faelle)
    gruppen = sum(f["gruppenfeld_zellen"] for f in faelle)
    mit_arm = sum(f["kopfangabe_mit_arm"] for f in faelle)
    ohne_arm = sum(f["kopfangabe_ohne_arm"] for f in faelle)
    anderer_arm = sum(f["kopfangabe_anderer_arm"] for f in faelle)
    keine = sum(f["keine_kopfangabe"] for f in faelle)
    kein_gruppen = sum(f["kein_gruppenfeld"] for f in faelle)
    outcome = sum(f["ueber_outcome_zeile"] for f in faelle)
    nur_kopf = sum(f["nur_als_kopfangabe"] for f in faelle)
    weder = sum(f["weder_noch"] for f in faelle)
    gezaehlt = mit_arm + ohne_arm
    quote = 100 * gezaehlt / gold if gold else 0.0

    zeilen: list[str] = []
    a = zeilen.append
    a("# Sprint 48: Kopfangaben unter den Goldzellen der 33 Budgetfaelle")
    a("")
    a(
        f"Grundgesamtheit: **{n}** `length_ohne_ergebnis`-Records aus "
        f"`yun699_p5_24000_20261118`, **{gold}** Goldzellen. Rein lesend: keine "
        "Netzaufrufe, keine Predictions geschrieben, keine eingefrorene Eingabe "
        "beruehrt. Die Entscheidungsvorlage `sprint48_nachzug_entscheidung_20261119.md` "
        "bleibt unveraendert."
    )
    a("")
    a("## 1. Befund")
    a("")
    a(
        f"- **{gruppen} von {gold} Goldzellen** sind Gruppengroessen "
        "(`intervention_group_size`, `comparator_group_size`). Nur diese koennen "
        "ueberhaupt eine Kopfangabe sein."
    )
    a(
        f"- **{gezaehlt} Goldzellen ({de(quote)} % aller Goldzellen) stehen als "
        f"`n = ...` im Tabellenkopf**: {mit_arm} mit belegtem Arm und {ohne_arm} ohne "
        f"Arm. Weitere {anderer_arm} treffen eine Kopfangabe nur mit einem anderen Arm."
    )
    a(
        f"- **{keine} Gruppengroessen haben keine Kopfangabe** im Dokument; "
        f"{kein_gruppen} Goldzellen sind Messwerte (Mittelwert, Streuung, Ereignisse)."
    )
    a(
        f"- Ueber die Outcome-Zeile erreichbar sind **{outcome} von {gold}** Goldzellen; "
        f"**{nur_kopf}** nur ueber eine Kopfangabe und **{weder}** weder ueber Zeile noch "
        "Kopfangabe (Fliesstext, andere Tabelle oder im Markdown nicht enthalten)."
    )
    a("")
    a("## 2. Je Record")
    a("")
    a(
        "| Record | Dokument | Gold | Gruppenfeld | Kopf m. Arm | Kopf o. Arm | and. Arm | "
                    "keine Kopfangabe | ueber Outcome-Zeile | nur Kopf (Wert) | weder/noch |"
    )
    a("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for f in sorted(faelle, key=lambda x: (-x["gold_zellen"], x["record_id"])):
        a(
            f"| `{f['record_id']}` | {f['dokument_id']} | {f['gold_zellen']} | "
            f"{f['gruppenfeld_zellen']} | {f['kopfangabe_mit_arm']} | "
            f"{f['kopfangabe_ohne_arm']} | {f['kopfangabe_anderer_arm']} | "
            f"{f['keine_kopfangabe']} | {f['ueber_outcome_zeile']} | "
            f"{f['nur_als_kopfangabe']} | {f['weder_noch']} |"
        )
    a("")
    a(
        "Spalten: `Kopf m. Arm` = Goldwert steht als `n = ...` im Kopf und der Arm ist "
        "belegt; `Kopf o. Arm` = Kopfangabe ohne belegten Arm; `and. Arm` = Wert nur "
        "mit anderem Arm; `keine Kopfangabe` = Gruppengroesse, deren Wert nicht als "
        "`n = ...` vorkommt; `ueber Outcome-Zeile` = Goldfeld kommt in "
        "`reachable_cells` mit einer echten Datenzeile vor (feldweise, wie im "
        "Benchmark); `nur Kopf (Wert)` = Wert steht als Kopfangabe mit belegtem Arm "
        "und das Feld kommt in keiner Datenzeile vor; `weder/noch` = keiner der "
        "beiden Wege fuer diesen Wert."
    )
    a("")
    a("## 3. Was das fuer den Kopf-Fakten-Prompt bedeutet")
    a("")
    a(
        f"Ein Kopf-Fakten-Prompt kann hoechstens die {gezaehlt} Goldzellen mit "
        f"belegter oder unbelegter Kopfangabe direkt liefern - das sind {de(quote)} % "
        f"der {gold} Goldzellen dieser 33 Faelle. Die uebrigen {gold - gezaehlt} "
        f"Zellen sind {kein_gruppen} Messwerte und {keine} Gruppengroessen ohne "
        "`n = ...` im Markdown; fuer sie aendert ein Kopf-Fakten-Prompt nichts."
    )
    a("")
    plan_ids = ("yun2024:30", "yun2024:252", "yun2024:421", "yun2024:672", "yun2024:678")
    plan = [f for rid in plan_ids for f in faelle if f["record_id"] == rid]
    if plan:
        p_gold = sum(f["gold_zellen"] for f in plan)
        p_kopf = sum(f["kopfangabe_mit_arm"] + f["kopfangabe_ohne_arm"] for f in plan)
        a(
            "In den fuenf Planfaellen aus der Diagnose sieht der Hebel so aus "
            f"({p_kopf} von {p_gold} Goldzellen sind Kopfangaben):"
        )
        a("")
        a("| Record | Gold | Gruppenfeld | Kopfangabe | mit Arm | ohne Arm |")
        a("|---|---:|---:|---:|---:|---:|")
        for f in plan:
            a(
                f"| `{f['record_id']}` | {f['gold_zellen']} | {f['gruppenfeld_zellen']} | "
                f"{f['kopfangabe_mit_arm'] + f['kopfangabe_ohne_arm']} | "
                f"{f['kopfangabe_mit_arm']} | {f['kopfangabe_ohne_arm']} |"
            )
        a("")
        voll = [f["record_id"] for f in plan
                if f["gold_zellen"] and f["kopfangabe_mit_arm"] + f["kopfangabe_ohne_arm"] == f["gold_zellen"]]
        leer = [f["record_id"] for f in plan if f["gruppenfeld_zellen"] and not (
            f["kopfangabe_mit_arm"] + f["kopfangabe_ohne_arm"]
        )]
        abdeckung = (
            ("Vollstaendig ueber Kopfangaben abgedeckt ist nur " + ", ".join(f"`{r}`" for r in voll) + ". ")
            if voll else "Kein Planfall ist vollstaendig ueber Kopfangaben abgedeckt. "
        )
        if leer:
            abdeckung += (
                "Ohne jeden Kopfangaben-Treffer bleiben " + ", ".join(f"`{r}`" for r in leer)
                + ": dort stehen die gesuchten Gruppengroessen nicht als `n = ...` im Markdown."
            )
        a(abdeckung)
        a("")
        a(
            "Der Hebel wirkt damit nur dort, wo die Aufgabe tatsaechlich nach "
            "Gruppengroessen fragt. Ob der Prompt das Reasoning entlastet, ist "
            "**nicht** gemessen: die Zaehlung zeigt nur die Obergrenze des Ertrags, "
            "nicht die Wirkung auf das Budget."
        )
    a("")
    a("## 4. Grenzen")
    a("")
    a(
        "- Gezaehlt wird gegen `Table.header_facts` des vorhandenen Parsers; eine "
        "Kopfangabe, die der Parser nicht erkennt (etwa in einer Bild-Caption), fehlt "
        "hier. Die Zahl ist damit eine Untergrenze."
    )
    a(
        "- Der Wertvergleich ist numerisch ueber `value`; dieselbe Zahl an anderer "
        "Stelle (etwa eine Stichprobe, die zufaellig `n` entspricht) kann einen "
        "Treffer erzeugen. Deshalb ist der Arm mit ausgewiesen."
    )
    a(
        "- `nur Kopf (Wert)` prueft den Wert, nicht nur das Feld: `reachable_cells` "
        "fuehrt eine Kopfangabe mit belegtem Arm als `(-1, feld)` und wuerde sonst "
        "auch dann einen Treffer melden, wenn die Tabelle eine andere Zahl druckt "
        "(`yun2024:252`: Tabelle `*n* = 398`, Gold 402)."
    )
    a(
        "- Kopfangaben koennen kursiv gesetzt sein (`*n* = 398`); gezaehlt wird, was "
        "`Table.header_facts` liefert, nicht ein eigener Textabgleich."
    )
    a(
        "- Gezaehlt werden **alle Tabellen des Dokuments**. Die Planwerte in "
        "`offline_struktur_20261118b/structure.json` beziehen sich auf je eine "
        "ausgewaehlte Tabelle und koennen deshalb kleiner sein (etwa `yun2024:421`: "
        "Plan 0, dokumentweit 4 Goldzellen ueber die Outcome-Zeile)."
    )
    parser = [f for f in faelle if f["parser_fehler"]]
    if parser:
        a("")
        a("Parserausfaelle: " + ", ".join(f"`{f['record_id']}`" for f in parser) + ".")
    return "\n".join(zeilen) + "\n"


def main() -> int:
    rows = [
        r for r in lies_jsonl(RUN)
        if r.get("fehlerklasse") == "length_ohne_ergebnis"
    ]
    records = {r["record_id"]: r for r in lies_jsonl(RECORDS)}
    cache: dict[str, str] = {}
    faelle = []
    for row in rows:
        record = records[row["record_id"]]
        pfad = ROOT / (record.get("document") or {}).get("path", "")
        key = str(pfad)
        if key not in cache:
            cache[key] = pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else ""
        faelle.append(zaehle_fall(row, record, cache[key]))

    summe = Counter()
    for f in faelle:
        for key in (
            "gold_zellen",
            "gruppenfeld_zellen",
            "kopfangabe_mit_arm",
            "kopfangabe_ohne_arm",
            "kopfangabe_anderer_arm",
            "keine_kopfangabe",
            "kein_gruppenfeld",
            "ueber_outcome_zeile",
            "nur_als_kopfangabe",
            "weder_noch",
        ):
            summe[key] += f[key]

    daten = {
        "sprint": 48,
        "frage": (
            "Wie viele Goldzellen der 33 Budgetfaelle sind Kopfangaben (n = ...) und "
            "damit fuer den Tabellenpfad nicht erreichbar?"
        ),
        "erzeugt_von": "public_benchmark/extended_benchmark/yun_full/zaehle_kopfangaben_sprint48.py",
        "nur_lesend": True,
        "netzaufrufe": 0,
        "lauf": RUN_ID,
        "records": len(faelle),
        "summe": dict(summe),
        "faelle": faelle,
    }
    AUSGABE.with_suffix(".json").write_text(
        json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    AUSGABE.with_suffix(".md").write_text(schreibe_md(faelle), encoding="utf-8")
    print(json.dumps({"records": len(faelle), **dict(summe)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
