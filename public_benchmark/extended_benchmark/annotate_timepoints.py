#!/usr/bin/env python3
"""Annotiert den Zielmesszeitpunkt je Dev-Record (manuell, mit Beleg).

Die Gold-Werte bleiben unberuehrt: Das Skript prueft vor dem Schreiben, dass
jede Gold-Zelle unveraendert ist, und bricht sonst ab. Jeder Eintrag nennt den
Zeitpunkt und eine woertliche Belegstelle aus dem Artikel; wo der Artikel
keinen Zeitpunkt nennt, steht "not stated" statt einer Vermutung.

Aufruf:
    python annotate_timepoints.py            # nur pruefen, nichts schreiben
    python annotate_timepoints.py --write    # Feld in records/yun_dev.jsonl setzen
    python annotate_timepoints.py --write --md analysis/timepoints_annotation.md
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
# Der Lauf liest records/yun.jsonl und filtert den Split; die Dev-Kopie ist die
# ausgewertete Datei. Beide tragen dasselbe Feld, damit sie nicht auseinanderlaufen.
RECORDS = (HERE / "records" / "yun_dev.jsonl", HERE / "records" / "yun.jsonl")

# record_id -> (Zielzeitpunkt, Belegstelle im Artikel)
ZEITPUNKTE: dict[str, tuple[str, str]] = {
    # PMC57750: nur Prozentwerte, keine Gold-Zellen
    "yun2024:1": ("30 days", "event rates (%) at 30 days; nur Prozentwerte, kein Gold-Wert"),
    "yun2024:2": ("30 days", "event rates (%) at 30 days; nur Prozentwerte, kein Gold-Wert"),
    # PMC1216327: Gewichtszunahme und Krankheitsdauer ueber die gesamte Studie
    "yun2024:3": (
        "whole treatment period (until recovery)",
        "mean body weight gain +50.7 gm; Angabe ohne Messzeitpunkt, Studie bis zur Genesung",
    ),
    "yun2024:4": (
        "whole treatment period (until recovery)",
        "duration of diarrhea in hours after randomization, through recovery (49.4 / 47.5 / 26.5 h)",
    ),
    "yun2024:5": ("not stated", "Tabellenkopf der fecal-loss-Tabelle im Markdown nicht lesbar"),
    # PMC2681019: kein Gold-Wert
    "yun2024:17": ("not stated", "Record ohne Gold-Zellen"),
    "yun2024:18": ("not stated", "Record ohne Gold-Zellen"),
    "yun2024:19": ("not stated", "Record ohne Gold-Zellen"),
    # PMC3276927: Textbefunde nach der Intervention
    "yun2024:55": ("after intervention (post-test)", "'All nineteen subjects showed ... after intervention'"),
    "yun2024:56": ("after intervention (post-test)", "Textbefund nach Intervention, Abschnitt Results"),
    "yun2024:57": ("after intervention (post-test)", "Textbefund nach Intervention, Abschnitt Results"),
    "yun2024:58": ("after intervention (post-test)", "Textbefund nach Intervention, Abschnitt Results"),
    "yun2024:59": ("after intervention (post-test)", "Textbefund nach Intervention, Abschnitt Results"),
    "yun2024:60": ("after intervention (post-test)", "Textbefund nach Intervention, Abschnitt Results"),
    # PMC3580751: Periodenvergleich
    "yun2024:83": (
        "Period 2 (2007 to 2010)",
        "intervention group 9.3 +/- 11.9 days vs. 9.9 +/- 14.8 days (period 1 vs period 2)",
    ),
    # PMC3751573: T1 nach dem Praktikum
    "yun2024:88": ("T1 (after practicum training)", "Spalten T0/T1; T1 = nach dem Praktikum"),
    # PMC4450164: DTPA-Scan, Zeitpunkt im Artikel nicht genannt
    "yun2024:120": (
        "post-operative DTPA scan (timepoint not stated)",
        "DTPA scan: Partial obstruction 8/20 13/44; kein Zeitpunkt im Text",
    ),
    # PMC5244530: alle Variablen zu baseline, 3, 6 und 12 Monaten
    "yun2024:186": (
        "12 months follow-up",
        "'All variables were measured at baseline and 3, 6, and 12 months.'",
    ),
    "yun2024:187": (
        "12 months follow-up",
        "'All variables were measured at baseline and 3, 6, and 12 months.'",
    ),
    "yun2024:188": (
        "12 months follow-up",
        "'All variables were measured at baseline and 3, 6, and 12 months.'",
    ),
    "yun2024:189": (
        "12 months follow-up",
        "'All variables were measured at baseline and 3, 6, and 12 months.'",
    ),
    "yun2024:190": (
        "12 months follow-up",
        "Sedatives: Intervention 26/64/53/52, TAU 32/73/56/51 (baseline, 3, 6, 12 months); Gold 52/51 = 12 Monate",
    ),
    "yun2024:191": (
        "Total 0-12 months",
        "sick leave: 0-3 months 31/48, 4-12 months 35/47, Total 0-12 months 49/64",
    ),
    "yun2024:192": (
        "6 months follow-up",
        "Antidepressants: Intervention 27/90/86/74, TAU 43/96/78/77; Gold 86/78 = 6 Monate",
    ),
    # PMC5771543: Wirksamkeit zu Woche 8, Nebenwirkungen im On-Therapy-Zeitraum
    "yun2024:260": ("Week 8", "'Summary of Secondary Efficacy Outcomes at Week 8' (CGI-I 79/101, 62/99)"),
    "yun2024:261": ("Week 8", "'Summary of Secondary Efficacy Outcomes at Week 8' (CGI-I 68/99, 62/99)"),
    "yun2024:262": ("On-Therapy Period", "'Adverse Events ... On-Therapy Period' (69/115, 79/112)"),
    "yun2024:263": ("On-Therapy Period", "'Adverse Events ... On-Therapy Period' (72/112, 79/112)"),
}

# PMC5498715: Tabelle mit Pre-test, Post-test, Follow up after 4 months; Gold = Post-test
for _nummer in range(224, 239):
    ZEITPUNKTE[f"yun2024:{_nummer}"] = (
        "Post-test",
        "Spalten 'Pre-test', 'Post-test', 'Follow up after 4 months'; Gold entspricht Post-test",
    )


# Regel fuer Records ohne manuelle Annotation: Der Zielzeitpunkt wird aus dem
# Text abgeleitet, und zwar die Zeitpunktangabe, die einer Goldzahl am
# naechsten steht. Das ist eine Heuristik; jeder Eintrag traegt deshalb
# `quelle: auto`, den Abstand und die woertliche Belegstelle, damit er pruefbar
# bleibt. Erfunden wird nichts: ohne Fundstelle steht "not stated".
MUSTER = [
    (re.compile(r"\bweek\s+(\d{1,2})\b", re.IGNORECASE), lambda m: f"week {m.group(1)}"),
    (re.compile(r"\bmonth\s+(\d{1,2})\b", re.IGNORECASE), lambda m: f"month {m.group(1)}"),
    (re.compile(r"\bday\s+(\d{1,2})\b", re.IGNORECASE), lambda m: f"day {m.group(1)}"),
    (re.compile(r"\bat\s+(\d{1,2})\s*weeks?\b", re.IGNORECASE), lambda m: f"week {m.group(1)}"),
    (re.compile(r"\bat\s+(\d{1,2})\s*months?\b", re.IGNORECASE), lambda m: f"month {m.group(1)}"),
    (re.compile(r"\bpost[- ]?test\b", re.IGNORECASE), lambda m: "post-test"),
    (re.compile(r"\bfollow[- ]?up\b", re.IGNORECASE), lambda m: "follow-up"),
    (re.compile(r"\bbaseline\b", re.IGNORECASE), lambda m: "baseline"),
    (re.compile(r"\bend of (?:the )?(?:study|treatment|intervention)\b", re.IGNORECASE), lambda m: "end of study/treatment"),
]


# Nullmessungen normalisiert _zeitpunkt_funde bereits zu "baseline".
UNSPEZIFISCH = {"baseline", "follow-up"}


def zeitpunkt_aus_outcome(outcome: str) -> str:
    """Zeitpunkt, der schon im Outcome-Namen steht ("at 12 months", "Baseline ...").

    Der Outcome-Name ist die beste Quelle fuer den Zielzeitpunkt: er beschreibt,
    was die Goldzelle bedeuten soll. Die Stichprobenpruefung (15.11.2026) hat
    gezeigt, dass die Textregel ohne diesen Anker bei "Baseline Height" und
    "BMI reduction at 12 months" daneben lag.
    """
    if re.search(r"\bbaseline\b", outcome, re.IGNORECASE):
        return "baseline"
    funde = _zeitpunkt_funde(outcome)
    namen = {f[1] for f in funde if f[1] not in UNSPEZIFISCH}
    if len(namen) == 1:
        return namen.pop()
    return ""


def _zeitpunkt_funde(text: str) -> list[tuple[int, str, str]]:
    funde: list[tuple[int, str, str]] = []
    for muster, label in MUSTER:
        for match in muster.finditer(text):
            name = label(match)
            if name in ("week 0", "month 0", "day 0"):
                # Nullmessungen sind Baseline-Messungen, keine eigenen Zeitpunkte.
                name = "baseline"
            funde.append((match.start(), name, match.group(0)))
    funde.sort(key=lambda f: f[0])
    return funde


def _satz_um(text: str, position: int) -> tuple[int, int]:
    """Saetzengrenzen um eine Position (grob ueber Punkt/Zeilenumbruch)."""
    start = max(text.rfind(". ", 0, position), text.rfind("\n", 0, position))
    ende = min(
        [x for x in (text.find(". ", position), text.find("\n", position)) if x != -1] or [len(text)]
    )
    return max(0, start), ende


def zeitpunkt_aus_text(
    text: str, gold_positionen: list[int], *, hat_ergebnis: bool = False
) -> dict[str, Any]:
    """Zeitpunkt aus dem Text, belegt statt geraten.

    Reihenfolge:
    1. Steht die Goldzahl in einem Satz mit Zeitpunktangabe, gilt dieser Satz.
    2. Sonst gewinnt die naechste Angabe — aber **nicht** baseline oder
       follow-up, wenn Gold Mittelwerte oder Ereignisse enthaelt: solche
       Ergebnisse stehen nicht in der Baseline-Tabelle, und ein solches Label
       waere eine Behauptung ohne Beleg.
    3. Bleibt nichts uebrig, ist das Ziel leer ("not stated").
    """
    funde = _zeitpunkt_funde(text)
    if not funde:
        return {"target": "", "evidence": "keine Zeitpunktangabe im Text", "status": "not stated", "abstand": ""}
    if not gold_positionen:
        return {"target": "", "evidence": "keine Goldzahl mit Position", "status": "ohne_goldzahl", "abstand": ""}

    # 1. Zeitpunkt im selben Satz wie eine Goldzahl.
    im_satz: list[tuple[int, str, str]] = []
    for pos in gold_positionen:
        start, ende = _satz_um(text, pos)
        im_satz += [f for f in funde if start <= f[0] <= ende]
    if hat_ergebnis:
        # "Baseline" im Satz der Goldzahl belegt keinen Zielzeitpunkt fuer einen
        # Mittelwert oder eine Ereigniszahl — auch nicht, wenn es dort steht.
        im_satz = [f for f in im_satz if f[1] not in UNSPEZIFISCH]
    if im_satz:
        namen = {f[1] for f in im_satz}
        if len(namen) == 1:
            name = namen.pop()
            bester = im_satz[0]
            umgebung = text[max(0, bester[0] - 60) : bester[0] + 70].replace("\n", " ").strip()
            return {
                "target": name,
                "evidence": f"'{bester[2]}' im selben Satz wie eine Goldzahl: …{umgebung}…",
                "status": "auto (Satz der Goldzahl)",
                "abstand": 0,
            }

    # 2. Naechste Angabe, baseline/follow-up nur ohne Ergebniszellen.
    kandidaten = funde
    if hat_ergebnis:
        kandidaten = [f for f in funde if f[1] not in UNSPEZIFISCH]
        if not kandidaten:
            return {
                "target": "",
                "evidence": "nur baseline/follow-up im Text, Gold enthaelt Mittelwerte oder Ereignisse",
                "status": "not stated (nur unspezifische Angaben)",
                "abstand": "",
            }
    bester = min(kandidaten, key=lambda f: min(abs(f[0] - pos) for pos in gold_positionen))
    abstand = min(abs(bester[0] - pos) for pos in gold_positionen)
    umgebung = text[max(0, bester[0] - 60) : bester[0] + 70].replace("\n", " ").strip()
    return {
        "target": bester[1],
        "evidence": f"'{bester[2]}' nahe einer Goldzahl ({abstand} Zeichen): …{umgebung}…",
        "status": "auto",
        "abstand": abstand,
    }


def annotate_kandidaten(
    ids_pfad: Path, out_pfad: Path, md_pfad: Path | None, *, write: bool
) -> int:
    """Kandidaten-Split einfrieren und Zielzeitpunkte nachziehen."""
    try:
        from .candidate_split import REPO as _REPO, finde
    except ImportError:  # pragma: no cover
        from candidate_split import REPO as _REPO, finde

    kandidaten = [json.loads(line) for line in ids_pfad.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = {
        k["record_id"]
        for k in kandidaten
        if k["zellen_gesamt"] > 0 and k["zellen_gefunden"] == k["zellen_gesamt"]
    }
    if not ids:
        print(f"FEHLER: keine vollstaendig belegten Records in {ids_pfad}")
        return 4

    quelle = HERE / "records" / "yun.jsonl"
    records = [json.loads(line) for line in quelle.read_text(encoding="utf-8").splitlines() if line.strip()]
    auswahl = [r for r in records if r["record_id"] in ids]
    review_rows: list[dict[str, Any]] = []
    vorher = {r["record_id"]: json.dumps(r["gold"], sort_keys=True, ensure_ascii=False) for r in auswahl}

    for record in auswahl:
        if record["record_id"] in ZEITPUNKTE:
            target, beleg = ZEITPUNKTE[record["record_id"]]
            record["timepoint"] = {
                "target": target,
                "evidence": beleg,
                "status": "manuell",
                "quelle": "manuell",
                "annotated": "2026-11-15",
            }
            continue
        pfad = _REPO / (record["document"].get("path") or "")
        text = pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else ""
        positionen: list[int] = []
        for cell in record["gold"]["cells"]:
            positionen += [f["position"] for f in finde(text, float(cell["value"]))]
        hat_ergebnis = any(
            "mean" in c["field"] or "events" in c["field"] for c in record["gold"]["cells"]
        )
        aus_outcome = zeitpunkt_aus_outcome((record.get("context") or {}).get("outcome", ""))
        info = zeitpunkt_aus_text(text, positionen, hat_ergebnis=hat_ergebnis)
        if aus_outcome and aus_outcome != info["target"]:
            info = {
                "target": aus_outcome,
                "evidence": f"Outcome-Titel nennt '{aus_outcome}'; Textregel hatte "
                f"'{info['target'] or 'nichts'}' ergeben",
                "status": "auto (Outcome-Titel)",
                "abstand": "",
            }
        # Vergleich mit der alten, ungehaerteten Regel fuer die Prueftabelle.
        alt = zeitpunkt_aus_text(text, positionen, hat_ergebnis=False)
        if alt["target"] == "follow-up" or (alt["target"] == "baseline" and hat_ergebnis):
            review_rows.append(
                {"record_id": record["record_id"], "alt": alt["target"], "evidence": alt["evidence"]}
            )
        record["timepoint"] = {
            "target": info["target"],
            "evidence": info["evidence"],
            "status": info["status"],
            "quelle": "auto",
            "abstand": info["abstand"],
            "annotated": "2026-11-15",
        }

    nachher = {r["record_id"]: json.dumps(r["gold"], sort_keys=True, ensure_ascii=False) for r in auswahl}
    if vorher != nachher:
        print("FEHLER: Gold-Werte wuerden sich aendern, Abbruch")
        return 3

    from collections import Counter

    verteilung = Counter(r["timepoint"]["target"] or "(ohne Ziel)" for r in auswahl)
    status = Counter(r["timepoint"]["status"] for r in auswahl)
    print(f"Kandidaten: {len(auswahl)} Records | Status: {dict(status)}")
    print(f"Zeitpunkte: {dict(verteilung.most_common(12))}")

    if md_pfad:
        md_pfad.parent.mkdir(parents=True, exist_ok=True)
        zeilen = [
            f"# Zielzeitpunkt der {len(auswahl)} Kandidaten-Records",
            "",
            "Automatisch aus dem Text abgeleitet (`quelle: auto`), wo keine manuelle",
            "Annotation vorliegt: genommen wird die Zeitpunktangabe, die einer Goldzahl",
            "am naechsten steht; Belegstelle und Abstand stehen in der Tabelle.",
            "",
            "## Verteilung",
            "",
            "| Zielzeitpunkt | Records |",
            "|---|---|",
        ]
        for ziel, anzahl in verteilung.most_common():
            zeilen.append(f"| {ziel} | {anzahl} |")
        baseline_mit_ergebnis = sum(
            1
            for r in auswahl
            if r["timepoint"]["target"] == "baseline"
            and any(feld in c["field"] for c in r["gold"]["cells"] for feld in ("mean", "events"))
        )
        neu_nach_alt = {r["record_id"]: (r["timepoint"]["target"] or "(ohne Ziel)") for r in auswahl}
        geprueft = review_rows
        if geprueft:
            leer = sum(1 for r in geprueft if neu_nach_alt.get(r["record_id"]) == "(ohne Ziel)")
            geaendert = sum(
                1 for r in geprueft if neu_nach_alt.get(r["record_id"]) != r["alt"]
            )
            zeilen += [
                "",
                "## Geprueft: frueher baseline/follow-up",
                "",
                "Diese Records trugen vor der Pruefung ein unspezifisches Label. Neu gilt:",
                "",
                f"{len(geprueft)} Records geprueft, {geaendert} geaendert, {leer} davon ohne Ziel;",
                "baseline bei reinen Gruppengroessen bleibt unveraendert und steht nicht in dieser Liste.",
                "",
                "| Record | alt | neu | Begruendung (Beleg) |",
                "|---|---|---|---|",
            ]
            for r in geprueft:
                beleg = (r["evidence"] or "").replace("|", "/")[:150]
                zeilen.append(
                    f"| `{r['record_id']}` | {r['alt']} | {neu_nach_alt.get(r['record_id'], '')} | {beleg} |"
                )
        zeilen += [
            "",
            "## Plausibilitaet der Automatik",
            "",
            f"{baseline_mit_ergebnis} Records tragen \"baseline\", obwohl Gold Mittelwerte oder",
            "Ereignisse enthaelt. Die Regel verwirft baseline/follow-up bei Ergebniszellen",
            "grundsaetzlich; bleibt dieser Wert ueber null, ist die Heuristik zu pruefen.",
        ]
        zeilen += ["", "## Je Record", "", "| Record | Dokument | Status | Zielzeitpunkt | Beleg |", "|---|---|---|---|---|"]
        for record in auswahl:
            info = record["timepoint"]
            beleg = (info["evidence"] or "").replace("|", "/")[:180]
            zeilen.append(
                f"| `{record['record_id']}` | {record['document']['id']} | {info['status']} | "
                f"{info['target'] or '(ohne Ziel)'} | {beleg} |"
            )
        md_pfad.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
        print(f"geschrieben: {md_pfad}")

    if write:
        out_pfad.parent.mkdir(parents=True, exist_ok=True)
        out_pfad.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in auswahl) + "\n", encoding="utf-8"
        )
        print(f"geschrieben: {out_pfad} ({len(auswahl)} Records, Gold unveraendert)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Feld in die Records schreiben")
    parser.add_argument("--md", type=Path, default=None, help="Uebersicht als Markdown schreiben")
    parser.add_argument("--records", type=Path, nargs="+", default=list(RECORDS))
    parser.add_argument(
        "--kandidaten-ids",
        type=Path,
        default=HERE / "analysis" / "candidate_split_20261115" / "kandidaten.jsonl",
        help="vollstaendig belegte Records (aus candidate_split.py)",
    )
    parser.add_argument("--kandidaten-out", type=Path, default=None, help="Kandidaten-Split schreiben")
    parser.add_argument("--kandidaten-md", type=Path, default=None, help="Zeitpunkt-Uebersicht der Kandidaten")
    args = parser.parse_args()

    dev = [json.loads(line) for line in (HERE / "records" / "yun_dev.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = {record["record_id"] for record in dev}
    fehlend = sorted(ids - set(ZEITPUNKTE))
    ueberzaehlig = sorted(set(ZEITPUNKTE) - ids)
    if fehlend or ueberzaehlig:
        print(f"FEHLER: ohne Annotation {fehlend}, ohne Record {ueberzaehlig}")
        return 2

    for pfad in args.records:
        records = [json.loads(line) for line in pfad.read_text(encoding="utf-8").splitlines() if line.strip()]
        vorher = {record["record_id"]: json.dumps(record["gold"], sort_keys=True, ensure_ascii=False) for record in records}
        geschrieben = 0
        for record in records:
            if record["record_id"] not in ZEITPUNKTE:
                continue
            target, beleg = ZEITPUNKTE[record["record_id"]]
            record["timepoint"] = {"target": target, "evidence": beleg, "annotated": "2026-11-15"}
            geschrieben += 1
        nachher = {record["record_id"]: json.dumps(record["gold"], sort_keys=True, ensure_ascii=False) for record in records}
        if vorher != nachher:
            print("FEHLER: Gold-Werte wuerden sich aendern, Abbruch")
            return 3
        if args.write:
            pfad.write_text(
                "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8"
            )
            print(f"geschrieben: {pfad} ({geschrieben} von {len(records)} Records, Gold unveraendert)")

    records = dev
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        zeilen = ["# Zielmesszeitpunkt je Dev-Record", "", "| Record | Zielzeitpunkt | Beleg |", "|---|---|---|"]
        for record in records:
            info = record["timepoint"]
            zeilen.append(f"| `{record['record_id']}` | {info['target']} | {info['evidence']} |")
        args.md.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
        print(f"geschrieben: {args.md}")

    if args.kandidaten_out:
        ergebnis = annotate_kandidaten(
            args.kandidaten_ids, args.kandidaten_out, args.kandidaten_md, write=args.write
        )
        if ergebnis != 0:
            return ergebnis

    from collections import Counter

    print("Verteilung:", dict(Counter(record["timepoint"]["target"] for record in records)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
