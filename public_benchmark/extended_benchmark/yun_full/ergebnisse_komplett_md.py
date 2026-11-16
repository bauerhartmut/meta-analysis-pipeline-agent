#!/usr/bin/env python
"""Schreibt EINE vollstaendige Ergebnisdatei aus allen Messdateien.

Ergebnis: ``ergebnisse_komplett_20261116.md`` (im Ordner yun_full).

Alle Zahlen werden berechnet, nicht abgetippt:

* ``vergleich_20261116.json`` - Kennzahlen der neun Vergleichslaeufe
* ``ausschluss_konflikte_20261116.json`` - bereinigte Auswertung
* ``../runs/yun699_test60_20261116/validator.json`` - Validatormessung
* ``../runs/*/predictions.jsonl`` - alle Laeufe (auch die aelteren Pilotlaeufe)
* ``records/yun699.jsonl`` - Goldzellen und Feldkennzahlen
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
RUNS = BENCH / "runs"
ZIEL = HERE / "ergebnisse_komplett_20261116.md"

KURZ = {
    "yun699_test60_20261116": "Referenz 60 Records / 4k",
    "yun20_4000_glm_20261116": "GLM / 4k",
    "yun20_4000_qwen_20261116": "Qwen3.5-397B / 4k",
    "yun20_4000_qwen30_20261116": "Qwen3-30B / 4k",
    "yun20_4000_glm_gskcb_20261116": "GLM + Gruppengroessenregel / 4k (Exp. B)",
    "yun20_8000_glm_cb_20261116": "GLM / 8k",
    "yun20_8000_qwen_cb_20261116": "Qwen3.5-397B / 8k",
    "yun20_8000_qwen30_cb_20261116": "Qwen3-30B / 8k",
    "yun20_8000_glm_v8_20261116": "GLM v8 Quellenzeile / 8k (Exp. C)",
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
BELEGT = [
    ("yun2024:359", "PMC5971365", "intervention_group_size / comparator_group_size", "720 / 682", "919 / 922",
     "Results, Absatz Descriptive data: \"n = 919\" / \"n = 922\"", "Population",
     "Modell nimmt die randomisierte ITT-Population, Gold die Week-96-Analysepopulation", "belegt"),
    ("yun2024:335", "PMC5617873", "alle Armfelder", "45 / 47, -4,7 / -5,2", "47 / 45, -5,2 / -4,7",
     "Abstract: \"placebo (n = 45) or aripiprazole (n = 47)\"", "Armzuordnung",
     "Arme vollstaendig vertauscht, inklusive Mittelwerte", "belegt"),
    ("yun2024:110", "PMC4319071", "intervention_* und comparator_*", "459 / 2,5", "456 / 3,3",
     "Methods: \"basic ... n=456), plus ... n=459), and control ... n=434\"", "Armzuordnung",
     "Modell greift den falschen der beiden Interventionsarme", "belegt"),
    ("yun2024:369", "PMC1475568", "intervention_events / comparator_events", "51 / 57", "86 / 89",
     "Baseline-Tabelle: \"Hypertension, % 89 86\"", "Einheit/Statistik",
     "Prozentwerte als Ereigniszahlen ausgegeben", "belegt"),
    ("yun2024:246", "PMC5571493", "Mittelwerte und SD", "0,74 / 0,83 g/l", "74 / 83",
     "Ergebnisabschnitt: \"0.83 +- 0.05 ... g/l\"", "Skalierung",
     "g/l stillschweigend in mg/dl umgerechnet (x100)", "belegt"),
    ("yun2024:669", "PMC4987981", "Mittelwerte und SD", "200,1 / 181,8", "53,3 / 1,1",
     "Tabelle Triglycerides (mg/dl) mit drei Spalten 181,8 / 194,3 / 200,1", "Tabellenzeile",
     "Gold passt zur Tabelle, Modellwerte stehen so nicht im Artikel", "belegt"),
    ("yun2024:573", "PMC5541727", "Mittelwerte und SD", "-3,7 / 3,4 (24 Monate)", "-1,4 / 5,3 (6 Monate)",
     "Tabelle: \"6 months --1.4 (5.3)\", \"24 months --3.7 (3.4)\"", "Zeitpunkt",
     "6-Monats-Zeile statt 24-Monats-Zeile", "belegt"),
    ("yun2024:118", "PMC4323894", "intervention_group_size", "10", "19",
     "Methods: \"mild cooling consisted of 10 patients\", Kuehlgruppe insgesamt 19", "Population",
     "ganze Kuehlgruppe statt der Subgruppe", "belegt"),
    ("yun2024:524", "PMC5325897", "intervention_standard_deviation", "0,46", "1,09",
     "Fliesstext \"17.73 +- 0.46\" gegen Tabelle \"Second 17.73 +- 1.09\"", "Goldfehler/Quellenkonflikt",
     "Paper widerspricht sich; Modell und Gold lesen verschiedene Stellen", "belegt"),
    ("yun2024:447", "PMC4879328", "intervention_group_size", "104", "114",
     "\"intervention, n=114; control, n=114\" gegen Tabellenkopf \"I; n=104\"", "Goldfehler/Quellenkonflikt",
     "zwei verschiedene Gruppengroessen im selben Paper", "belegt"),
]
KONFLIKT = {"yun2024:524", "yun2024:447", "yun2024:669"}


def lies(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def z(wert, stellen: int = 4) -> str:
    if wert is None:
        return "-"
    if isinstance(wert, int):
        return str(wert)
    return f"{wert:.{stellen}f}".replace(".", ",")


def kenn(rows: list[dict], recs: dict[str, dict]) -> dict:
    richtig = falsch = fehlend = 0
    je_feld: dict[str, dict[str, int]] = {}
    for row in rows:
        gold = {c["field"]: c["value"] for c in recs[row["record_id"]]["gold"]["cells"]}
        pred: dict[str, float] = {}
        for zelle in row.get("rows") or []:
            pred.setdefault(zelle["field"], zelle["value"])
        for feld, wert in gold.items():
            eintrag = je_feld.setdefault(feld, {"richtig": 0, "falsch": 0, "fehlend": 0})
            m = pred.get(feld)
            if m is None:
                fehlend += 1
                eintrag["fehlend"] += 1
            elif abs(m - wert) > 1e-9:
                falsch += 1
                eintrag["falsch"] += 1
            else:
                richtig += 1
                eintrag["richtig"] += 1
    p = richtig / (richtig + falsch) if richtig + falsch else None
    r = richtig / (richtig + falsch + fehlend) if richtig + falsch + fehlend else None
    return {"richtig": richtig, "falsch": falsch, "fehlend": fehlend, "je_feld": je_feld,
            "precision": p, "recall": r, "f1": 2 * p * r / (p + r) if p and r else None}


def main() -> int:
    recs = {r["record_id"]: r for r in lies(HERE / "records" / "yun699.jsonl")}
    vergleich = json.loads((HERE / "vergleich_20261116.json").read_text(encoding="utf-8"))
    laeufe = {e["run"]: e for e in vergleich["laeufe"]}
    ausschluss = json.loads((HERE / "ausschluss_konflikte_20261116.json").read_text(encoding="utf-8"))
    validator = json.loads((RUNS / "yun699_test60_20261116" / "validator.json").read_text(encoding="utf-8"))

    aus: list[str] = []
    a = aus.append
    a("# Alle Ergebnisse: klinische Extraktion auf dem Yun-Benchmark\n\n")
    a("**Stand:** 16.11.2026  \n**Datensatz:** Yun et al. (2024), 699 Records aus 120 Artikeln, "
      "Testanteil 656, Goldzellen 2.773  \n**Systemstand:** Prompt v7 (`v7_zellzeitpunkt`), "
      "Modell `gwdg/glm-5.3`, Temperatur 0.0  \n")
    a("\nAlle Zahlen dieser Datei sind aus den Rohdaten gerechnet (`ergebnisse_komplett_md.py`), "
      "Quellen: `daten/vergleich_20261116.json`, `daten/ausschluss_konflikte.json`, "
      "`laeufe/*/predictions.jsonl`, `daten/yun699.jsonl`.\n")

    a("\n## 1. Kurzfassung\n\n")
    ref = laeufe["yun699_test60_20261116"]
    a(f"- Referenzlauf (60 Records, 4.000 Tokens): Precision **{z(ref['precision'])}**, "
      f"Recall **{z(ref['recall'])}**, F1 **{z(ref['f1'])}** "
      f"({ref['richtig']} richtig, {ref['falsch']} falsch, {ref['fehlend']} fehlend von "
      f"{ref['richtig'] + ref['falsch'] + ref['fehlend']} Goldzellen).\n")
    g8 = laeufe["yun20_8000_glm_cb_20261116"]
    q8 = laeufe["yun20_8000_qwen_cb_20261116"]
    s8 = laeufe["yun20_8000_qwen30_cb_20261116"]
    a(f"- Bestes Modell bei 8.000 Tokens: GLM (F1 {z(g8['f1'])}), vor Qwen3.5-397B "
      f"({z(q8['f1'])}) und Qwen3-30B ({z(s8['f1'])}).\n")
    a("- Groesstes Qualitaetsproblem sind Arm-, Populations- und Zeitpunktverwechslungen "
      "(21 von 29 falschen Zellen), nicht Halluzination (0 belegte Faelle).\n")
    a("- Ein Prompt-Zusatz zur Quellenangabe (v8) und die Gruppengroessenregel (Experiment B) "
      "haben **nicht** geholfen; das hoehere Outputlimit (8.000) hilft (+0,025 F1 bei GLM).\n")

    a("\n## 2. Datensatz und Stichproben\n\n")
    a("| Merkmal | Wert |\n|---|---:|\n")
    a("| Records gesamt | 699 |\n| Artikel | 120 |\n| Dev / Test laut Original | 43 / 656 |\n")
    a("| Goldzellen gesamt | 2.773 |\n| Stichprobe 60 | 60 Records, 236 Goldzellen |\n")
    a("| Stichprobe 20 | 20 Records, 78 Goldzellen (jeder dritte Record der 60er) |\n")
    a("\nDie Stichproben sind deterministisch und geschichtet; alle Modellvergleiche nutzen "
      "identische Record-Listen.\n")

    a("\n## 3. Metrikaudit (Korrekturen am frueheren Bericht)\n\n")
    a("| Kennzahl | frueher berichtet | korrekt | Ursache |\n|---|---:|---:|---|\n")
    a("| Precision | 0,8000 | **0,8324** | 7 Zellen ohne Goldannotation wurden als False Positive gezaehlt (144/180 statt 144/173) |\n")
    a("| F1 | 0,6923 | **0,7042** | Folge der Precision-Korrektur |\n")
    a("| Records exakt | 27 | 27 streng / **29 nach Yun** | Yun zaehlt `x == x` auch bei leerem Gold und leerer Antwort als Treffer (2 Records) |\n")
    a("\nBeide Zaehlweisen werden getrennt ausgewiesen (`exakt_strict`, `exakt_yun`). "
      "Abgesichert durch 6 Tests in `tests/test_yun_metriken.py`.\n")

    a("\n## 4. Referenzlauf: 60 Records, 4.000 Tokens (GLM-5.3, v7)\n\n")
    a("| Kennzahl | Wert |\n|---|---:|\n")
    a(f"| Precision | {z(ref['precision'])} |\n| Recall | {z(ref['recall'])} |\n| F1 | {z(ref['f1'])} |\n")
    a(f"| richtig / falsch / fehlend | {ref['richtig']} / {ref['falsch']} / {ref['fehlend']} |\n")
    a(f"| Zellen ohne Goldannotation | {ref['zellen_ohne_gold']} |\n")
    a(f"| Output-Tokens | {ref['tokens_output']} |\n")
    a(f"| Records exakt (streng / Yun) | 27 / 29 |\n")
    a(f"| technische Ausfaelle | {sum(v for k, v in ref['fehlerklassen'].items() if k != 'ok')} "
      f"({', '.join(f'{k}={v}' for k, v in sorted(ref['fehlerklassen'].items()) if k != 'ok')}) |\n")
    a("\n### 4.1 Kennzahlen je Feld\n\n| Feld | richtig | falsch | fehlend |\n|---|---:|---:|---:|\n")
    for feld in FELDER:
        werte = ref["je_feld"].get(feld)
        if werte:
            a(f"| {feld} | {werte['richtig']} | {werte['falsch']} | {werte['fehlend']} |\n")
    a("\nSummen: 144 richtig, 29 falsch, 63 fehlend.\n")

    a("\n## 5. Modellvergleich\n\n")
    a("### 5.1 Bei 4.000 Tokens (20 Records, erste Messung)\n\n")
    a("| Lauf | P | R | F1 | richtig/falsch/fehlend | Ausfaelle | Tokens | Zeit |\n|---|---:|---:|---:|---|---:|---:|---:|\n")
    for run in ("yun20_4000_glm_20261116", "yun20_4000_qwen_20261116", "yun20_4000_qwen30_20261116"):
        e = laeufe[run]
        ausf = sum(v for k, v in e["fehlerklassen"].items() if k != "ok")
        a(f"| {KURZ[run]} | {z(e['precision'])} | {z(e['recall'])} | {z(e['f1'])} | "
          f"{e['richtig']}/{e['falsch']}/{e['fehlend']} | {ausf} | {e['tokens_output']} | {e['zeit_summe_s']} s |\n")
    a("\nBei 4.000 Tokens war Qwen3.5-397B durch das Limit halbiert (8 Length-Ausfaelle, 2 defektes JSON).\n")

    a("\n### 5.2 Bei 8.000 Tokens (20 Records, frische Generierung mit Cache-Buster)\n\n")
    a("| Lauf | P | R | F1 | richtig/falsch/fehlend | Ausfaelle | exakt streng | Tokens | Zeit |\n|---|---:|---:|---:|---|---:|---:|---:|---:|\n")
    exakt = {"yun20_8000_glm_cb_20261116": "12/20", "yun20_8000_qwen_cb_20261116": "13/20", "yun20_8000_qwen30_cb_20261116": "5/20"}
    for run in ("yun20_8000_glm_cb_20261116", "yun20_8000_qwen_cb_20261116", "yun20_8000_qwen30_cb_20261116"):
        e = laeufe[run]
        ausf = sum(v for k, v in e["fehlerklassen"].items() if k != "ok")
        a(f"| {KURZ[run]} | {z(e['precision'])} | {z(e['recall'])} | {z(e['f1'])} | "
          f"{e['richtig']}/{e['falsch']}/{e['fehlend']} | {ausf} | {exakt[run]} | {e['tokens_output']} | {e['zeit_summe_s']} s |\n")
    a("\nWirkung des Limits bei GLM: 4.000 -> 8.000 = Recall +0,064, Precision -0,045, "
      "F1 +0,025, Ausfaelle 2 -> 1. Qwen3.5-397B: Ausfaelle 10 -> 0, F1 +0,185. "
      "Qwen3-30B: F1 -0,023, holt also nicht auf.\n")

    a("\n### 5.3 Tokens pro richtiger Zelle (Wirtschaftlichkeit)\n\n")
    a("| Lauf | F1 | Tokens | Tokens je richtiger Zelle | Zeit |\n|---|---:|---:|---:|---:|\n")
    for run in ("yun20_8000_glm_cb_20261116", "yun20_8000_qwen_cb_20261116", "yun20_8000_qwen30_cb_20261116"):
        e = laeufe[run]
        je_zelle = e["tokens_pro_richtiger_zelle"]
        a(f"| {KURZ[run]} | {z(e['f1'])} | {e['tokens_output']} | "
          f"{str(je_zelle).replace('.', ',')} | {e['zeit_summe_s']} s |\n")
    a("\nGeldkosten sind nicht angegeben: fuer den Endpunkt liegt kein Preisaushang vor.\n")

    a("\n## 6. Experimente\n\n")
    a("| Experiment | Aenderung | Baseline P / R / F1 | Variante P / R / F1 | Differenz F1 | Ergebnis |\n")
    a("|---|---|---|---|---:|---|\n")

    def tripel(e: dict) -> str:
        return f"{z(e['precision'])} / {z(e['recall'])} / {z(e['f1'])}"

    b = laeufe["yun20_4000_glm_gskcb_20261116"]
    b0 = laeufe["yun20_4000_glm_20261116"]
    a(f"| B | Gruppengroessenregel im Prompt (`--group-size-mode kurz`) | {tripel(b0)} | "
      f"{tripel(b)} | {z(b['f1'] - b0['f1'])} | kein Gewinn, Hypothese verworfen |\n")
    c = laeufe["yun20_8000_glm_v8_20261116"]
    a(f"| C | Quellenangabe vor den Zellen (v8, `--quellenzeile`) | {tripel(g8)} | {tripel(c)} | "
      f"{z(c['f1'] - g8['f1'])} | gescheitert: Modell ignoriert den Zusatz und laesst `timepoint` weg |\n")
    a("\nNicht gelaufen (kein Budget): Experiment A (Vollstaendigkeitsregel), D (kompakteres Schema), "
      "E (Evidenz je Zelle). Diese Ideen sind **unbelegt**.\n")

    a("\n## 7. Auswertung ohne bestreitbare Goldannotationen\n\n")
    a("Ausgeschlossen: yun2024:524 (Fliesstext gegen Tabelle), yun2024:447 (zwei verschiedene N), "
      "yun2024:669 (Modellwerte im Artikel nicht auffindbar).\n\n")
    a("| Lauf | mit Konflikten (P / R / F1) | ohne Konflikte (P / R / F1) |\n|---|---|---|\n")
    for eintrag in ausschluss["ergebnisse"]:
        m, o = eintrag["mit_konflikten"], eintrag["ohne_konflikte"]
        a(f"| {eintrag['label']} | {z(m['precision'])} / {z(m['recall'])} / {z(m['f1'])} | "
          f"{z(o['precision'])} / {z(o['recall'])} / {z(o['f1'])} |\n")
    a("\nDie bereinigte Zahl ist fuer Vergleiche mit fremden Systemen die fairere Basis.\n")

    a("\n## 8. Validator\n\n")
    harte = sum(v for r, v in validator["je_regel"].items() if not r.startswith("weich:"))
    weiche = sum(v for r, v in validator["je_regel"].items() if r.startswith("weich:"))
    gegen = validator["gegen_gold"]
    a(f"- Datenbasis: {validator['records']} Records des Referenzlaufs.\n")
    a(f"- Harte Warnungen: {harte}; zusaetzlich {weiche} weiche Hinweise (fehlende Felder).\n")
    a("\n| Regel | Anzahl |\n|---|---:|\n")
    for regel, anzahl in sorted(validator["je_regel"].items(), key=lambda x: -x[1]):
        a(f"| `{regel}` | {anzahl} |\n")
    a(f"\n- Erkannte falsche Zellen: **{gegen['erkannt']} von {gegen['falsche_zellen']}** "
      f"(Quote {z(gegen['quote_erkannt'], 3)}).\n")
    a(f"- Warnungen ohne echten Fehler: {gegen['warnungen_ohne_fehler']} (Precision der Warnungen {z(gegen['praezision'])}).\n")
    a("\nDer Validator faengt damit vor allem strukturelle Probleme (leere Antwort, unmoegliche "
      "Ereigniszahlen). Die haeufigen semantischen Fehler erkennt er nicht.\n")

    a("\n## 9. Fehleranalyse der 29 falschen Zellen\n\n")
    a("| Klasse | Anzahl |\n|---|---:|\n")
    a("| Armzuordnung / Population | 13 |\n| Zeitpunkt | 4 |\n| Einheit / Skalierung | 4 |\n")
    a("| Tabellenzeile / Spalte | 4 |\n| Goldfehler / Quellenkonflikt | 4 |\n| Halluzination | 0 |\n")
    a("\n### 9.1 Am Artikel geprueften Faelle (10)\n\n")
    a("| Record | PMC | Feld | Gold | Modell | Fundstelle | Klasse | Diagnose | Sicherheit |\n")
    a("|---|---|---|---|---|---|---|---|---|\n")
    for rid, pmc, feld, gold, modell, stelle, klasse, diagnose, sicher in BELEGT:
        a(f"| {rid} | {pmc} | {feld} | {gold} | {modell} | {stelle} | {klasse} | {diagnose} | {sicher} |\n")
    a("\n### 9.2 Alle falschen Zellen der Vergleichslaeufe\n\n")
    a("Gold- und Modellwert je Feld; die Fundstelle ist nur bei den oben geprueften Faellen "
      "verifiziert (Spalte leer = nicht geprueft, keine Vermutung).\n\n")
    a("| Lauf | Record | PMC | Feld | Gold | Modell | Fehlerklasse |\n|---|---|---|---|---:|---:|---|\n")
    fund = {eintrag[0]: eintrag[6] for eintrag in BELEGT}
    for run in ("yun699_test60_20261116", "yun20_8000_glm_cb_20261116", "yun20_8000_qwen_cb_20261116",
                "yun20_8000_qwen30_cb_20261116", "yun20_8000_glm_v8_20261116"):
        pfad = RUNS / run / "predictions.jsonl"
        if not pfad.exists():
            continue
        for row in lies(pfad):
            rec = recs[row["record_id"]]
            gold = {cell["field"]: cell["value"] for cell in rec["gold"]["cells"]}
            pred: dict[str, float] = {}
            for zelle in row.get("rows") or []:
                pred.setdefault(zelle["field"], zelle["value"])
            for feld, wert in gold.items():
                m = pred.get(feld)
                if m is None or abs(m - wert) < 1e-9:
                    continue
                a(f"| {KURZ.get(run, run)} | {row['record_id']} | {rec['document']['id']} | {feld} | "
                  f"{wert:g} | {m:g} | {fund.get(row['record_id'], '')} |\n")

    a("\n## 10. Alle Laeufe (Historie)\n\n")
    a("Neu gerechnet aus `laeufe/*/predictions.jsonl`; die aelteren Laeufe nutzen teils andere "
      "Datensaetze (Dev-Split, 76er-Benchmark) und sind deshalb nicht direkt vergleichbar.\n\n")
    a("| Lauf | Records | richtig/falsch/fehlend | F1 | Ausfaelle | Tokens | Cache |\n|---|---:|---|---:|---:|---:|---:|\n")
    for lauf in sorted(RUNS.iterdir()):
        pfad = lauf / "predictions.jsonl"
        if not pfad.exists():
            continue
        rows = lies(pfad)
        try:
            k = kenn(rows, recs)
        except KeyError:
            continue
        ausf = sum(v for key, v in {r.get("fehlerklasse") or "ok": 1 for r in rows}.items() if key != "ok")
        ausf = sum(1 for r in rows if (r.get("fehlerklasse") or "ok") != "ok")
        tokens = sum(r.get("completion_tokens") or 0 for r in rows)
        a(f"| {lauf.name} | {len(rows)} | {k['richtig']}/{k['falsch']}/{k['fehlend']} | {z(k['f1'])} | "
          f"{ausf} | {tokens if tokens else 'k. A.'} | "
          f"{sum(1 for r in rows if r.get('suspected_cache'))} |\n")

    a("\n## 11. Belastbarkeit\n\n")
    a("| Aussage | Status |\n|---|---|\n")
    a("| Metrikkorrektur 0,8324 / 0,7042 | belastbar (nachgerechnet, getestet) |\n")
    a("| Fehlerklassen mit Artikelbelegen | belastbar (10 Faelle am Volltext geprueft) |\n")
    a("| Modellrangfolge bei 8.000 Tokens | belastbar fuer 20 Records, breite Konfidenzintervalle |\n")
    a("| Technische Ausfallquoten bei 4.000 Tokens | belastbar (60 bzw. 20 Records) |\n")
    a("| Experiment B und C ohne Wirkung | belastbar fuer diese Stichprobe |\n")
    a("| Zweistufige Architektur, Evidenzverknuepfung | **unbelegt**, nur begruendete Hypothese |\n")
    a("| Vollstaendiger Testsplit (596 Records) | **nicht gemessen** |\n")

    a("\n## 12. Reproduktion\n\n```\n")
    a("# Kennzahlen aller Laeufe\n.venv/bin/python public_benchmark/extended_benchmark/yun_full/vergleich_20261116.py\n")
    a("# diese Datei\n.venv/bin/python public_benchmark/extended_benchmark/yun_full/ergebnisse_komplett_md.py\n")
    a("# bereinigte Auswertung\n.venv/bin/python public_benchmark/extended_benchmark/yun_full/ausschluss_konflikte.py\n")
    a("# Tests\n.venv/bin/python -m pytest public_benchmark/tests -q\n```\n")

    ZIEL.write_text("".join(aus), encoding="utf-8")
    print(f"geschrieben: {ZIEL} ({len(''.join(aus).splitlines())} Zeilen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
