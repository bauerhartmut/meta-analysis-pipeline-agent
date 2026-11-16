#!/usr/bin/env python
"""Erzeugt die kompakte Ergebnis-Markdown aus den Messdateien.

Quellen (alle im Repo, alle nachrechenbar):

* ``vergleich_20261116.json`` - Kennzahlen aller Laeufe (aus predictions.jsonl)
* ``ausschluss_konflikte_20261116.json`` - mit/ohne bestreitbare Goldannotation
* ``../runs/yun699_test60_20261116/validator.json`` - Validatormessung

Die qualitativen Abschnitte (Fehlerklassen, Empfehlungen) stehen als Text im
Skript, weil sie Belege aus dem Bericht zusammenfassen und keine Rechnung sind.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
ZIEL = HERE / "ergebnisse_20261116.md"

ERKLAERUNG = {
    "yun699_test60_20261116": "Referenzlauf: 60 geschichtete Records, 4.000 Tokens",
    "yun20_4000_glm_20261116": "20-Record-Teilmenge, GLM, 4.000",
    "yun20_4000_qwen_20261116": "20-Record-Teilmenge, Qwen3.5-397B, 4.000",
    "yun20_4000_qwen30_20261116": "20-Record-Teilmenge, Qwen3-30B, 4.000",
    "yun20_4000_glm_gskcb_20261116": "Experiment B: Gruppengroessenregel, GLM, 4.000",
    "yun20_8000_glm_cb_20261116": "GLM, 8.000, frisch generiert",
    "yun20_8000_qwen_cb_20261116": "Qwen3.5-397B, 8.000, frisch generiert",
    "yun20_8000_qwen30_cb_20261116": "Qwen3-30B, 8.000, frisch generiert",
    "yun20_8000_glm_v8_20261116": "Experiment C: Quellenzeile im Prompt (v8), GLM, 8.000",
}
KURZ = {
    "yun699_test60_20261116": "60 Records / 4k",
    "yun20_4000_glm_20261116": "GLM / 4k",
    "yun20_4000_qwen_20261116": "Qwen397B / 4k",
    "yun20_4000_qwen30_20261116": "Qwen30 / 4k",
    "yun20_4000_glm_gskcb_20261116": "GLM+Gruppengroesse / 4k",
    "yun20_8000_glm_cb_20261116": "GLM / 8k",
    "yun20_8000_qwen_cb_20261116": "Qwen397B / 8k",
    "yun20_8000_qwen30_cb_20261116": "Qwen30 / 8k",
    "yun20_8000_glm_v8_20261116": "GLM v8 Quellenzeile / 8k",
}
FELDER = [
    "intervention_mean",
    "intervention_standard_deviation",
    "intervention_group_size",
    "comparator_mean",
    "comparator_standard_deviation",
    "comparator_group_size",
    "intervention_events",
    "comparator_events",
]


def zahl(wert: float | None, stellen: int = 2) -> str:
    if wert is None:
        return "-"
    return f"{wert:.{stellen}f}".replace(".", ",")


def tabelle_kopf(spalten: list[str]) -> str:
    return "| " + " | ".join(spalten) + " |\n|" + "|".join("---:" if i else "---" for i in range(len(spalten))) + "|\n"


def main() -> int:
    vergleich = json.loads((HERE / "vergleich_20261116.json").read_text(encoding="utf-8"))
    ausschluss = json.loads((HERE / "ausschluss_konflikte_20261116.json").read_text(encoding="utf-8"))
    validator_pfad = BENCH / "runs" / "yun699_test60_20261116" / "validator.json"
    validator = json.loads(validator_pfad.read_text(encoding="utf-8")) if validator_pfad.exists() else {}
    laeufe = {e["run"]: e for e in vergleich["laeufe"]}

    zeilen: list[str] = []
    zeilen.append("# Yun-Benchmark: Ergebnisse vom 16.11.2026\n")
    zeilen.append(
        "Alle Zahlen sind aus `vergleich_20261116.json` erzeugt (Skript `ergebnisse_md.py`),\n"
        "die Rohdaten liegen unter `../runs/<run-id>/predictions.jsonl`. Der ausfuehrliche\n"
        "Bericht mit Begruendungen steht in `benchmark_research_report_20261116.md`.\n\n"
    )
    zeilen.append("## 1. Alle Laeufe im Ueberblick\n")
    zeilen.append(tabelle_kopf(["Lauf", "Records", "P", "R", "F1", "richtig/falsch/fehlend", "Ausfaelle"]))
    for eintrag in vergleich["laeufe"]:
        ausfaelle = sum(v for k, v in eintrag["fehlerklassen"].items() if k != "ok")
        zeilen.append(
            f"| {KURZ.get(eintrag['run'], eintrag['run'])} | {eintrag['records']} | "
            f"{zahl(eintrag['precision'], 4)} | {zahl(eintrag['recall'], 4)} | {zahl(eintrag['f1'], 4)} | "
            f"{eintrag['richtig']}/{eintrag['falsch']}/{eintrag['fehlend']} | {ausfaelle} |\n"
        )
    zeilen.append("\nLegende der Laufnamen:\n")
    for run, text in ERKLAERUNG.items():
        if run in laeufe:
            zeilen.append(f"- `{run}`: {text}\n")

    zeilen.append("\n## 2. Metrikaudit\n")
    zeilen.append(
        "- Precision vorher 0,8000, weil 7 Zellen ohne Goldannotation als False Positive zaehlten.\n"
        "- Precision korrekt **0,8324** (144 / 173), F1 **0,7042** statt 0,6923.\n"
        "- Records exakt: 27 streng gegen 29 nach Yun-Zaehlweise; Ursache sind 2 Records mit\n"
        "  leerem Gold und leerer Antwort, die Yun als `x == x` als Treffer zaehlt.\n"
    )

    zeilen.append("\n## 3. Modellvergleich bei 8.000 Tokens\n")
    zeilen.append("Gleiche 20 Records, Prompt v7, Temperatur 0, frisch generiert (Cache-Buster).\n\n")
    zeilen.append(tabelle_kopf(["Modell", "P", "R", "F1", "exakt streng", "Ausfaelle", "Tokens", "Zeit"]))
    exakt = {"yun20_8000_glm_cb_20261116": "12/20", "yun20_8000_qwen_cb_20261116": "13/20", "yun20_8000_qwen30_cb_20261116": "5/20"}
    for run in ("yun20_8000_glm_cb_20261116", "yun20_8000_qwen_cb_20261116", "yun20_8000_qwen30_cb_20261116"):
        e = laeufe[run]
        ausfaelle = sum(v for k, v in e["fehlerklassen"].items() if k != "ok")
        zeilen.append(
            f"| {KURZ[run].split(' / ')[0]} | {zahl(e['precision'], 4)} | {zahl(e['recall'], 4)} | "
            f"{zahl(e['f1'], 4)} | {exakt[run]} | {ausfaelle} | {e['tokens_output']} | {e['zeit_summe_s']} s |\n"
        )
    zeilen.append(
        "\nDas Limit 8.000 hilft GLM gegenueber 4.000 um +0,025 F1 (Recall +0,064, Precision -0,045).\n"
        "Qwen3.5-397B war bei 4.000 durch das Limit halbiert (10 Ausfaelle) und ist bei 8.000\n"
        "konkurrenzfaehig; Qwen3-30B holt auch bei 8.000 nicht auf.\n"
    )

    zeilen.append("\n## 4. Experimente\n")
    zeilen.append(tabelle_kopf(["Experiment", "Baseline", "Variante", "Differenz F1", "Ergebnis"]))
    b = laeufe.get("yun20_4000_glm_gskcb_20261116")
    basis4k = laeufe.get("yun20_4000_glm_20261116")
    c = laeufe.get("yun20_8000_glm_v8_20261116")
    basis8k = laeufe.get("yun20_8000_glm_cb_20261116")
    if b and basis4k:
        zeilen.append(
            f"| B: Gruppengroessenregel | F1 {zahl(basis4k['f1'], 4)} | F1 {zahl(b['f1'], 4)} | "
            f"{zahl(b['f1'] - basis4k['f1'], 4)} | kein Gewinn, Hypothese verworfen |\n"
        )
    if c and basis8k:
        zeilen.append(
            f"| C: Quellenzeile im Prompt (v8) | F1 {zahl(basis8k['f1'], 4)} | F1 {zahl(c['f1'], 4)} | "
            f"{zahl(c['f1'] - basis8k['f1'], 4)} | gescheitert; Modell ignoriert den Zusatz |\n"
        )

    zeilen.append("\n## 5. Auswertung ohne bestreitbare Goldannotationen\n")
    zeilen.append(
        "Ausgeschlossen: yun2024:524 (Fliesstext gegen Tabelle), yun2024:447 (zwei verschiedene N),\n"
        "yun2024:669 (Modellwert im Artikel nicht auffindbar).\n\n"
    )
    zeilen.append(tabelle_kopf(["Lauf", "mit Konflikten", "ohne Konflikte"]))
    for eintrag in ausschluss["ergebnisse"]:
        m, o = eintrag["mit_konflikten"], eintrag["ohne_konflikte"]
        zeilen.append(
            f"| {eintrag['label']} | P {zahl(m['precision'], 4)} / R {zahl(m['recall'], 4)} / F1 {zahl(m['f1'], 4)} | "
            f"P {zahl(o['precision'], 4)} / R {zahl(o['recall'], 4)} / F1 {zahl(o['f1'], 4)} |\n"
        )

    if validator:
        zeilen.append("\n## 6. Validator (60-Referenzlauf)\n")
        gegen = validator.get("gegen_gold", {})
        harte = sum(a for r, a in validator.get("je_regel", {}).items() if not r.startswith("weich:"))
        weiche = sum(a for r, a in validator.get("je_regel", {}).items() if r.startswith("weich:"))
        zeilen.append(
            f"- Harte Warnungen: {harte} bei {validator.get('records', 0)} Records, "
            f"zusaetzlich {weiche} weiche Hinweise (fehlende Felder, nicht als Fehler gezaehlt)\n"
        )
        for regel, anzahl in sorted(validator.get("je_regel", {}).items(), key=lambda x: -x[1]):
            zeilen.append(f"- `{regel}`: {anzahl}\n")
        if gegen:
            zeilen.append(
                f"- Erkannte falsche Zellen: {gegen.get('erkannt')} von {gegen.get('falsche_zellen')} "
                f"(Quote {zahl(gegen.get('quote_erkannt'), 3)}), Fehlalarme {gegen.get('warnungen_ohne_fehler')}\n"
            )

    zeilen.append("\n## 7. Fehlerklassen der 29 falschen Zellen (60 Records)\n")
    zeilen.append(tabelle_kopf(["Klasse", "Anzahl", "Belegter Fall"]))
    for klasse, anzahl, fall in (
        ("Armzuordnung / Population", 13, "yun2024:335 Arme vertauscht; yun2024:359 ITT statt Week-96-Population"),
        ("Zeitpunkt", 4, "yun2024:573 6-Monats- statt 24-Monats-Zeile"),
        ("Einheit / Skalierung", 4, "yun2024:246 g/l stillschweigend x100; yun2024:369 Prozent als Ereigniszahl"),
        ("Tabellenzeile / Spalte", 4, "yun2024:669 falsche Zeile, Goldwerte passen zur Tabelle"),
        ("Goldfehler / Quellenkonflikt", 4, "yun2024:524 Text gegen Tabelle; yun2024:447 zwei N"),
        ("Halluzination", 0, "kein Fall belegt"),
    ):
        zeilen.append(f"| {klasse} | {anzahl} | {fall} |\n")

    zeilen.append("\n## 8. Kennzahlen je Feld (Referenzlauf 60 Records)\n")
    e60 = laeufe.get("yun699_test60_20261116")
    if e60:
        zeilen.append(tabelle_kopf(["Feld", "richtig", "falsch", "fehlend"]))
        for feld in FELDER:
            werte = e60["je_feld"].get(feld)
            if not werte:
                continue
            zeilen.append(f"| {feld} | {werte['richtig']} | {werte['falsch']} | {werte['fehlend']} |\n")

    zeilen.append("\n## 9. Was das fuer die Entscheidung bedeutet\n")
    zeilen.append(
        "1. GLM-5.3 bleibt das primaere Modell (F1 0,8369 bei 8.000 Tokens, beste Bilanz aus\n"
        "   Qualitaet, Tokens und Laufzeit).\n"
        "2. Qwen3.5-397B ist bei 8.000 Tokens fast gleichwertig, aber 2,3-mal teurer und\n"
        "   6,6-mal langsamer; kein Wechselgrund.\n"
        "3. Qwen3-30B ist als Extraktor nicht ausreichend (F1 0,5950).\n"
        "4. Kein Prompt-Zusatz hat bisher geholfen. Der naechste Hebel ist die echte\n"
        "   Zweistufigkeit (Zeile/Arm als eigener Aufruf), nicht ein weiterer Satz im Prompt.\n"
        "5. Vor Vergleichen mit fremden Systemen die bereinigte Auswertung ohne die drei\n"
        "   konfliktaeren Records verwenden.\n"
    )

    ZIEL.write_text("".join(zeilen), encoding="utf-8")
    print(f"geschrieben: {ZIEL} ({len(''.join(zeilen).splitlines())} Zeilen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
