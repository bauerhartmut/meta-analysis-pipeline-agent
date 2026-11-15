#!/usr/bin/env python3
"""Annotiert die Zielzeitpunkte der 76 Records der zweiten Kohorte und friert sie ein.

Vorgehen wie bei den 186 Records (`annotate_timepoints.py`): zuerst der
Outcome-Titel, dann die Zeitpunktangabe im Satz der Goldzahl, sonst die
naechstgelegene Angabe. Jeder Eintrag traegt Beleg, Status und Abstand; wo der
Artikel keinen Zeitpunkt nennt, steht ein leerer Zielzeitpunkt statt einer
Vermutung. Die Goldzellen werden vor und nach dem Schreiben verglichen und
muessen identisch bleiben.

Das Ergebnis ist `records/yun_test76_ziel.jsonl`; der SHA-256 der Datei wird
ausgegeben und in `analysis/run186_20261115/error_analysis/teststrategie.md`
eingetragen.

Aufruf::

    python annotate_test76.py                    # nur pruefen, nichts schreiben
    python annotate_test76.py --write --md .../test76_annotation.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from annotate_timepoints import zeitpunkt_aus_outcome, zeitpunkt_aus_text  # noqa: E402
from candidate_split import REPO, finde  # noqa: E402

QUELLE = HERE / "records" / "yun_test76_ohne_ziel.jsonl"
ZIEL = HERE / "records" / "yun_test76_ziel.jsonl"

# Manuelle Korrekturen nach der Stichprobenpruefung (Record -> (Ziel, Beleg)).
# Leer, solange die Automatik in der Stichprobe keinen Fehler zeigt.
MANUELL: dict[str, tuple[str, str]] = {
    # PMC3195393: Tabelle "Preintervention phase / Postintervention phase",
    # n = 463 gegen n = 562; die Goldwerte sind die Postinterventions-Spalte
    # ("from 10.8 to 8.5% ... postintervention").
    "yun2024:51": ("postintervention phase", "Tabelle: Preintervention n=463 / Postintervention n=562; 'from 10.8 to 8.5% ... postintervention'"),
    "yun2024:52": ("postintervention phase", "'overall restraint rate ... from 11.5% to 13.6% postintervention'"),
    "yun2024:53": ("postintervention phase", "'increase in the use of intermittent restraint, from 0.7 to 5.1%'"),
    "yun2024:54": ("postintervention phase", "Postinterventions-Spalte der Tabelle (Wissensscore 6.23 gegen 5.51)"),
    # PMC3309311: einmalige MRT-Auswertung, kein Messzeitpunkt genannt
    "yun2024:63": ("MRI assessment (timepoint not stated)", "'Various MRI findings were assessed among the above 3 groups'; kein Zeitpunkt im Abstract"),
    # PMC3321528: Handkraft-Subgruppe, Aufnahmewerte
    "yun2024:71": ("at admission", "'at admission'; Handkraft der bei Aufnahme untersuchten Subgruppe (n = 21)"),
    # PMC5086025: Binge Eating prae/post, Gold sind die Post-Werte
    "yun2024:178": ("postintervention", "'assessed pre- and postintervention and 3-months postintervention'; 7/26 gegen 14/26"),
    # PMC5976949: Nabelschnurblut, Entnahme bei der Geburt
    "yun2024:365": ("at birth (cord blood)", "'adipokine concentration in cord blood from women with GDM'"),
    # PMC3929816: Tierversuch, Messung waehrend der Operation
    "yun2024:286": ("during the operation", "'intra-abdominal pressure was maintained 12 mm Hg and 20 mm Hg during the operation'"),
    # PMC4678179: Ueberlebenszeit und Ansprechrate bis Studienende
    "yun2024:398": ("end of follow-up", "'Median overall survival (OS) was 6.9 and 6.1 months for GV and GP arms'"),
    "yun2024:399": ("end of study/treatment", "'Response rates were not significantly different' — Ansprechen ueber die Studiendauer"),
    # PMC4140238: Outcome nennt den Zeitpunkt selbst
    "yun2024:445": ("visit 3B at 7 min", "Outcome-Titel 'ocular itching for visit 3B at 7 min' (Conjunctival Allergen Challenge)"),
    # PMC4144850: Anämie im 21-Monats-Follow-up
    "yun2024:479": ("21-month follow-up", "'1,655 were located at the 21-month follow-up survey'"),
    # PMC5419060: Fragebogen prae/post Training (Gold = Post)
    "yun2024:503": ("post-training", "'questionnaire was administered pre- and post-training'; 63% auf 96% (CHC A)"),
    "yun2024:504": ("post-training", "'from 58% to 93% at CHC B'"),
    "yun2024:505": ("post-training", "'from 60% to 97% at CDC C'"),
    "yun2024:506": ("post-training", "'from 63% to 97% at CDC D'"),
    # PMC3493722: Eradikations-/Compliancewerte am Therapieende (1- oder 2-Wochen-Kur)
    "yun2024:626": ("end of treatment", "'bismuth-containing quadruple rescue therapy over a 1- or 2-week period'"),
    # PMC3510731: einmalige Websitzung, Klickverhalten
    "yun2024:630": ("single session (timepoint not stated)", "'Median time in seconds ... Clicked on Protocol link'; einmalige Sitzung"),
    # PMC5773985: Volumen und Wirkeintritt intraoperativ, Analgesiedauer postoperativ
    "yun2024:655": ("intraoperative", "'mean volume ... used' waehrend der Operation (4.15 vs 4.12 ml)"),
    "yun2024:656": ("intraoperative (onset)", "'subjective onset of action in bupivacaine group (3.00 +- 1.08 min)'"),
    "yun2024:657": ("intraoperative (onset)", "'on pinprick test ... 7.40 +- 1.93 min'"),
    "yun2024:659": ("postoperative (until first analgesic request)", "'mean duration of postoperative analgesia ... 508.92 vs 1840.84 minutes'"),
    # PMC5712123: Schmerzwerte im postoperativen Verlauf, Gold bei 24 h
    "yun2024:693": ("24 h postoperatively", "'morphine requirement at 24 h'; Schmerz zu 0, 2, 4, 24 und 48 h"),
    "yun2024:694": ("24 h postoperatively", "Schmerz bei Bewegung, gleiche Messreihe (0, 2, 4, 24, 48 h)"),
}

# PMC4215531: MCCB-Tabelle mit Pre/Post, Training ueber 4 Wochen; Gold = Post.
for _nummer in range(289, 296):
    MANUELL[f"yun2024:{_nummer}"] = (
        "post (after 4-week training)",
        "MCCB-Tabelle: Zeilen 'Pre' und 'Post'; 'after 4-week' Training",
    )

# Vokabeln, die einen Messzeitpunkt anzeigen koennen. Fehlt jede, berichtet der
# Abstract nur eine Messung; dann gilt "after intervention (post-test)", wie bei
# den Dev-Records 55-60 (Textbefund nach Intervention).
ZEITVOKABEL = re.compile(
    r"\b(weeks?|months?|days?|hours?|years?|baseline|follow[- ]?up|post[- ]?test"
    r"|end of (?:study|treatment|intervention))\b",
    re.IGNORECASE,
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def gold_hash(records: list[dict[str, Any]]) -> str:
    roh = json.dumps([r["gold"] for r in records], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(roh.encode("utf-8")).hexdigest()


def annotiere(record: dict[str, Any]) -> dict[str, Any]:
    if record["record_id"] in MANUELL:
        target, beleg = MANUELL[record["record_id"]]
        return {
            "target": target,
            "evidence": beleg,
            "status": "manuell",
            "quelle": "manuell",
            "abstand": "",
            "annotated": "2026-11-16",
        }
    pfad = REPO / (record["document"].get("path") or "")
    text = pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else ""
    zellen = record["gold"]["cells"]
    if all(str(c["field"]).endswith("_group_size") for c in zellen):
        # Reine Arm-Groessen: der Zeitpunkt ist die Aufnahme, wie bei 325/328.
        return {
            "target": "baseline",
            "evidence": "Gold enthaelt nur Gruppengroessen (Arm-Eigenschaft, Zeitpunkt Aufnahme)",
            "status": "Regel (nur Gruppengroessen)",
            "quelle": "manuell",
            "abstand": "",
            "annotated": "2026-11-16",
        }
    positionen: list[int] = []
    for cell in record["gold"]["cells"]:
        positionen += [treffer["position"] for treffer in finde(text, float(cell["value"]))]
    hat_ergebnis = any("mean" in c["field"] or "events" in c["field"] for c in record["gold"]["cells"])
    aus_outcome = zeitpunkt_aus_outcome((record.get("context") or {}).get("outcome", ""))
    info = zeitpunkt_aus_text(text, positionen, hat_ergebnis=hat_ergebnis)
    if not info["target"] and not ZEITVOKABEL.search(text):
        # Abstract nennt keinen Zeitpunkt und enthaelt keine Zeitvokabel: die
        # berichtete Messung ist die Messung nach der Intervention.
        info = {
            "target": "after intervention (post-test)",
            "evidence": "Abstract nennt keinen Messzeitpunkt und enthaelt keine Zeitvokabel; "
            "einzige berichtete Messung nach der Intervention",
            "status": "Regel (keine Zeitvokabel)",
            "abstand": "",
        }
    if aus_outcome and aus_outcome != info["target"]:
        info = {
            "target": aus_outcome,
            "evidence": f"Outcome-Titel nennt '{aus_outcome}'; Textregel hatte "
            f"'{info['target'] or 'nichts'}' ergeben",
            "status": "auto (Outcome-Titel)",
            "abstand": "",
        }
    return {
        "target": info["target"],
        "evidence": info["evidence"],
        "status": info["status"],
        "quelle": "auto",
        "abstand": info["abstand"],
        "annotated": "2026-11-16",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--md", type=Path, default=None)
    args = parser.parse_args()

    records = read_jsonl(QUELLE)
    if len(records) != 76:
        print(f"FEHLER: {len(records)} Records statt 76 in {QUELLE}")
        return 2
    vorher = gold_hash(records)

    for record in records:
        record["timepoint"] = annotiere(record)

    if gold_hash(records) != vorher:
        print("FEHLER: Gold-Werte wuerden sich aendern, Abbruch")
        return 3

    ziele = Counter(r["timepoint"]["target"] or "(ohne Ziel)" for r in records)
    status = Counter(r["timepoint"]["status"] for r in records)
    baseline_mit_ergebnis = [
        r["record_id"]
        for r in records
        if r["timepoint"]["target"] == "baseline"
        and any(("mean" in c["field"] or "events" in c["field"]) for c in r["gold"]["cells"])
    ]
    print(f"{len(records)} Records, {sum(len(r['gold']['cells']) for r in records)} Zellen")
    print("Status:", dict(status))
    print("Ziele:", dict(ziele.most_common(12)))
    print(f"baseline mit Mittelwert/Ereignissen: {len(baseline_mit_ergebnis)} {baseline_mit_ergebnis}")
    print("Gold-Hash vorher/nachher gleich:", gold_hash(records) == vorher)

    if args.write:
        ZIEL.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
        digest = hashlib.sha256(ZIEL.read_bytes()).hexdigest()
        print(f"geschrieben: {ZIEL} ({len(records)} Records)")
        print(f"SHA-256: {digest}")
    else:
        probe = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
        print("SHA-256 (Vorschau, nicht geschrieben):", hashlib.sha256(probe.encode("utf-8")).hexdigest())

    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        zeilen = [
            "# Zielzeitpunkte der 76 Records (zweite Kohorte)",
            "",
            "Automatisch abgeleitet wie bei den 186 Records (`annotate_test76.py`, `quelle: auto`),",
            "Goldzellen unveraendert. Jeder Eintrag nennt Belegstelle und Abstand.",
            "",
            "## Verteilung",
            "",
            "| Zielzeitpunkt | Records |",
            "|---|---|",
        ]
        for ziel, anzahl in ziele.most_common():
            zeilen.append(f"| {ziel} | {anzahl} |")
        zeilen += ["", "## Je Record", "", "| Record | Ziel | Status | Beleg |", "|---|---|---|---|"]
        for record in records:
            info = record["timepoint"]
            beleg = (info["evidence"] or "").replace("|", "/")[:170]
            zeilen.append(
                f"| `{record['record_id']}` | {info['target'] or '(ohne Ziel)'} | {info['status']} | {beleg} |"
            )
        args.md.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
        print(f"geschrieben: {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
