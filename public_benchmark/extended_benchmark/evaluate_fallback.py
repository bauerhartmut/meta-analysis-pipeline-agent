#!/usr/bin/env python3
"""Bewertung der Rueckfallregel (v6_target_fallback).

Das Modell nennt je Zelle den benutzten Messzeitpunkt. Dieses Skript trennt die
Zellen in zwei Klassen und zaehlt sie getrennt:

* **zieltreu**: Zelle nennt den im Record annotierten Zielzeitpunkt
* **rueckfall**: Zelle nennt einen anderen Zeitpunkt (dann muss sie stimmen,
  sonst ist die Rueckfallregel schaedlich)

Zusaetzlich: Auslassungen je Feld, Gesamtmetriken und die Zeitdistanz der
Rueckfaelle in Monaten (aus den Labels, ohne Modell).
"""

from __future__ import annotations

import argparse
import re
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from candidate_split import REPO  # noqa: E402
from check_timepoints import rang  # noqa: E402
from evaluate_extended import _close, _f1, _safe_div, evaluate_numeric, read_jsonl  # noqa: E402
from stage_extraction import normalisiere  # noqa: E402


def klassifiziere(target: str, label: str) -> str:
    """Ordnet eine Zelle einer Klasse zu (Eingaben bereits normalisiert)."""
    if not target:
        return "ohne_ziel"
    if not label:
        return "ohne_zeitpunkt"
    if label == target:
        return "zieltreu"
    return "rueckfall"


NUMMER = re.compile(r"^(\d{1,3})$")
ZEIT_LABEL = re.compile(r"^(week|month|day)\s+(\d{1,3})$")


def normalisiere_label(label: str, target: str) -> tuple[str, str]:
    """Ergaenzt eine Einheit nur, wenn sie belegt ist; gibt (label, status).

    Status: "ok" (vergleichbar), "leer" (keine Angabe), "unklar" (Zahl ohne
    belegte Einheit). Die Einheit kommt ausschliesslich aus dem annotierten
    Zielzeitpunkt: "24" bei Ziel "week 24" ist Woche 24, "24" bei Ziel
    "month 6" bleibt unklar. Aus der Zahl allein wird nichts abgeleitet, und
    "0" wird nur dann zu baseline, wenn das Ziel baseline sagt.
    """
    roh = normalisiere(label)
    ziel = normalisiere(target)
    if not roh or roh in ("not applicable", "running text", "not stated"):
        return "", "leer"
    if NUMMER.match(roh):
        zahl = int(roh)
        if zahl == 0 and ziel in ("baseline", "week 0", "month 0", "day 0"):
            return "baseline", "ok"
        treffer = ZEIT_LABEL.match(ziel)
        if treffer and int(treffer.group(2)) == zahl:
            return f"{treffer.group(1)} {zahl}", "ok"
        return "", "unklar"
    return roh, "ok"


def arme_gemischt(cells: list[dict[str, Any]], target: str) -> bool:
    """Wahr, wenn die Arme verschiedene Zeitpunkte tragen.

    Ein Zeitpunkt gilt je Arm; weicht der Komparator vom Interventionsarm ab,
    wurde ueber die Arme hinweg gemischt (z. B. Intervention Woche 24,
    Komparator Baseline) und die Zuordnung ist nicht mehr eindeutig.
    """
    pro_arm: dict[str, set[str]] = defaultdict(set)
    for cell in cells:
        # Rohvergleich: auch '24' gegen '0' ist ein Unterschied, unabhaengig
        # davon, ob die Einheit belegt ist.
        label = normalisiere(cell.get("timepoint") or "")
        if label and label not in ("not applicable", "running text", "not stated"):
            pro_arm[str(cell.get("arm"))].add(label)
    if len(pro_arm) < 2:
        return False
    mengen = list(pro_arm.values())
    return any(m != mengen[0] for m in mengen[1:])


EINHEIT_WORT = r"(week|month|day|year|hour)"
LABEL_EINHEIT_ERST = re.compile(rf"^{EINHEIT_WORT}s?\s*(\d{{1,3}})$", re.I)
LABEL_ZAHL_ERST = re.compile(rf"^(\d{{1,3}})\s*{EINHEIT_WORT}s?$", re.I)


def label_mit_einheit(roh: str) -> tuple[str, int] | None:
    """Liest "week 24" und "12 months" in dieselbe Form ("month 12")."""
    treffer = LABEL_EINHEIT_ERST.match(roh)
    if treffer:
        return treffer.group(1).lower(), int(treffer.group(2))
    treffer = LABEL_ZAHL_ERST.match(roh)
    if treffer:
        return treffer.group(2).lower(), int(treffer.group(1))
    return None


def _zahl_muster(zahl: int) -> str:
    """Sucht eine ganze Zahl, aber nicht als Teil von 12,5 oder 112."""
    return rf"(?<![\d.,]){zahl}(?![\d.,])"


def einheiten_im_artikel(zahl: int, text: str) -> set[str]:
    """Einheiten, die der Artikel fuer diese nackte Zahl belegt.

    Vier Muster: "Week 12", "12 weeks", "Weeks (0 12 24)" und Zahlenreihen mit
    Einheit in derselben Zeile ("0, 12, 24 weeks"). Dezimalzahlen liefern keine
    Evidenz fuer die Ganzzahl. Mehrere Einheiten heissen: mehrdeutig.
    """
    einheiten: set[str] = set()
    if not text:
        return einheiten
    zahl_muster = _zahl_muster(zahl)
    for treffer in re.finditer(rf"\b{EINHEIT_WORT}s?\s*{zahl_muster}", text, re.I):
        einheiten.add(treffer.group(1).lower())
    for treffer in re.finditer(rf"{zahl_muster}\s*[- ]?\s*{EINHEIT_WORT}s?\b", text, re.I):
        einheiten.add(treffer.group(1).lower())
    for treffer in re.finditer(rf"\b{EINHEIT_WORT}s?\s*\(([^)]{{0,80}})\)", text, re.I):
        if re.search(zahl_muster, treffer.group(2)):
            einheiten.add(treffer.group(1).lower())
    # Zahlenreihe mit Einheit in derselben Zeile: "0, 12, 24 weeks".
    for zeile in text.splitlines():
        for treffer in re.finditer(rf"((?:\d{{1,3}}\s*[,;/]?\s*){{2,}}){EINHEIT_WORT}s?\b", zeile, re.I):
            reihe = {int(wert) for wert in re.findall(r"\d{1,3}", treffer.group(1))}
            if zahl in reihe:
                einheiten.add(treffer.group(2).lower())
    return einheiten


def belegstufe(label: str, ziel: str, artikel: str) -> tuple[str, str]:
    """Einheit eines Zeitpunktlabels mit Belegstufe; gibt (label, stufe).

    Stufen: "gedruckt" (Einheit steht im Label), "artikel" (genau eine Einheit
    fuer die Zahl im Artikeltext), "ziel" (nur aus dem annotierten Ziel, also
    zirkulaer und nur fuer Treffer brauchbar), "unklar" (nichts belegt,
    mehrdeutig oder Widerspruch zum Ziel), "leer" (keine Zeitpunktangabe).
    """
    roh = normalisiere(label)
    ziel_norm = normalisiere(ziel)
    if not roh or roh in ("not applicable", "running text", "not stated"):
        return "", "leer"
    gedruckt = label_mit_einheit(roh)
    if gedruckt:
        return f"{gedruckt[0]} {gedruckt[1]}", "gedruckt"
    if not NUMMER.match(roh):
        return roh, "gedruckt"
    zahl = int(roh)
    ziel_treffer = ZEIT_LABEL.match(ziel_norm)
    ziel_einheit = ziel_treffer.group(1).lower() if ziel_treffer else ""
    if zahl == 0:
        if ziel_norm in ("baseline", "week 0", "month 0", "day 0"):
            return "baseline", "ziel"
        return "", "unklar"
    einheiten = einheiten_im_artikel(zahl, artikel)
    if len(einheiten) == 1:
        einheit = next(iter(einheiten))
        if ziel_einheit and ziel_treffer and int(ziel_treffer.group(2)) == zahl and ziel_einheit != einheit:
            # Artikel und Ziel nennen fuer dieselbe Zahl verschiedene Einheiten.
            return "", "unklar"
        return f"{einheit} {zahl}", "artikel"
    if len(einheiten) > 1:
        return "", "unklar"
    if ziel_treffer and int(ziel_treffer.group(2)) == zahl:
        return f"{ziel_einheit} {zahl}", "ziel"
    return "", "unklar"


def rueckfall_intervall(zaehler: dict[str, int]) -> dict[str, Any]:
    """Rueckfallquote als Intervall: unklar zaehlt einmal nicht, einmal mit."""
    zieltreu = zaehler.get("zieltreu", 0)
    rueckfall = zaehler.get("rueckfall", 0)
    unklar = zaehler.get("unklar", 0)
    nenner = zieltreu + rueckfall + unklar
    if nenner == 0:
        return {"untere_grenze": None, "obere_grenze": None, "zaehler": {"zieltreu": zieltreu, "rueckfall": rueckfall, "unklar": unklar}}
    return {
        "untere_grenze": round(rueckfall / nenner, 4),
        "obere_grenze": round((rueckfall + unklar) / nenner, 4),
        "zaehler": {"zieltreu": zieltreu, "rueckfall": rueckfall, "unklar": unklar},
    }


def wilson(treffer: int, n: int) -> tuple[float, float] | None:
    """95-Prozent-Wilson-Intervall fuer einen Anteil (ohne scipy)."""
    if n == 0:
        return None
    p = treffer / n
    z = 1.96
    nenner = 1 + z * z / n
    mitte = (p + z * z / (2 * n)) / nenner
    rand = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / nenner
    return (round(max(0.0, mitte - rand), 4), round(min(1.0, mitte + rand), 4))


def zahlen_in_zeile(zahlen: list[float], text: str) -> bool:
    """Stehen alle Zahlen in derselben Textzeile? (Triage fuer Gold-Konflikte)"""
    if not zahlen:
        return False
    for zeile in text.splitlines():
        if all(_zahl_steht(zahl, zeile) for zahl in zahlen):
            return True
    return False


def _zahl_steht(zahl: float, zeile: str) -> bool:
    for text in {f"{zahl:g}", f"{zahl:.2f}".rstrip("0").rstrip("."), f"{zahl:.2f}"}:
        if text and (text in zeile or text.replace(".", ",") in zeile):
            return True
    return False


def bestaetigter_konflikt(record_id: str) -> bool:
    """Steht der Record in der geprueften Gold-Konfliktliste (analyze_errors) ?"""
    if not record_id:
        return False
    try:
        from analyze_errors import GEPRUEFTE_FAELLE
    except Exception:  # pragma: no cover - Analyse-Modul ist optional
        return False
    return any(schluessel[0] == record_id for schluessel in GEPRUEFTE_FAELLE)


def arm_klasse(
    cells: list[dict[str, Any]], gold_werte: list[float], artikel: str, target: str, record_id: str = ""
) -> str:
    """Trennt Modell- von Goldmischung.

    "arm_konsistent": beide Arme am selben Zeitpunkt. "arm_gemischt_gold_bestaetigt":
    Gold-Konflikt steht geprueft in `GEPRUEFTE_FAELLE`. "arm_gemischt_gold_kandidat":
    die Arme sind gemischt und die Goldwerte stehen im Artikel in derselben Zeile
    (Hinweis auf Goldmischung, kein Beweis bei gefalteten Tabellen).
    "arm_gemischt_modell": Mischung ohne diesen Hinweis.
    """
    if not arme_gemischt(cells, target):
        return "arm_konsistent"
    if bestaetigter_konflikt(record_id):
        return "arm_gemischt_gold_bestaetigt"
    if len(gold_werte) >= 2 and zahlen_in_zeile(gold_werte, artikel):
        return "arm_gemischt_gold_kandidat"
    return "arm_gemischt_modell"


def header_belegt(header: str, artikel: str) -> bool:
    """Steht der Zeitpunkt-Header woertlich im Artikel? (v7-Pruefung)"""
    if not header or not artikel:
        return False
    ruhig = " ".join(header.split()).lower()
    return ruhig in " ".join(artikel.split()).lower()


def pruefe_v7_zeile(row: dict[str, Any], artikel: str) -> dict[str, Any]:
    """Formale Pruefung einer v7-Zeile: fallback gesetzt, stimmig, Header belegt.

    Inhaltlich geprueft wird nur, was mechanisch pruefbar ist. `fallback_konisstent`
    ist None, wenn kein Zeitpunkt vorliegt.
    """
    fallback = row.get("fallback")
    header = str(row.get("timepoint_header") or "")
    ziel = normalisiere(row.get("target_timepoint") or "")
    labels = {normalisiere(cell.get("timepoint") or "") for cell in (row.get("rows") or [])}
    labels.discard("")
    befund: dict[str, Any] = {
        "fallback_gesetzt": isinstance(fallback, bool),
        "header_belegt": header_belegt(header, artikel),
        "ein_zeitpunkt": len(labels) <= 1,
        "fallback_konsistent": None,
    }
    if isinstance(fallback, bool) and len(labels) == 1 and ziel:
        # Belegstufe statt Rohvergleich: "24" gegen "week 24" ist derselbe
        # Zeitpunkt, "12" ohne Artikelbeleg bleibt unbestimmt (None).
        label, stufe = belegstufe(next(iter(labels)), ziel, artikel)
        if label and stufe in ("gedruckt", "artikel", "ziel"):
            befund["fallback_konsistent"] = (label != ziel) if fallback else (label == ziel)
    return befund


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--records", type=Path, default=HERE / "records" / "yun_dev.jsonl")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    records = read_jsonl(args.records)
    by_id = {str(record["record_id"]): record for record in records}
    rows = read_jsonl(HERE / "runs" / args.run / "predictions.jsonl")
    predictions = {str(row["record_id"]): row for row in rows}

    zaehler = Counter()
    pro_feld: dict[str, Counter] = defaultdict(Counter)
    distanzen: list[float] = []
    rueckfall_beispiele: list[dict[str, Any]] = []
    unklar_beispiele: list[dict[str, Any]] = []
    arm_gemischt: list[str] = []
    fehlend: Counter[str] = Counter()
    belegstufen: Counter[str] = Counter()
    stufen_klassen: Counter[str] = Counter()
    treffer_belegt = 0
    treffer_nur_ziel = 0
    arm_klassen: Counter[str] = Counter()
    arm_kandidaten: list[dict[str, Any]] = []
    gemischte_zellen = 0
    zellen_mit_label = 0

    def artikel_text(record: dict[str, Any]) -> str:
        pfad = (record.get("document") or {}).get("path") or ""
        datei = REPO / pfad if pfad else None
        if not datei or not datei.exists():
            return ""
        return datei.read_text(encoding="utf-8", errors="replace")

    for record_id, record in by_id.items():
        gold = {(cell["field"], cell.get("arm")): float(cell["value"]) for cell in record["gold"]["cells"]}
        target = normalisiere((record.get("timepoint") or {}).get("target") or "")
        if "not stated" in target:
            # Kein Zielzeitpunkt im Record: Zellen lassen sich nicht als
            # zieltreu oder Rueckfall bewerten und zaehlen als "ohne_ziel".
            target = ""
        cells = (predictions.get(record_id, {}).get("predicted") or {}).get("cells", [])
        artikel = artikel_text(record)
        gesehen: set[tuple[str, str | None]] = set()
        for cell in cells:
            key = (cell["field"], cell.get("arm"))
            label, label_status = normalisiere_label(cell.get("timepoint") or "", target)
            # Belegstufe unabhaengig von der Klassifikation: sie sagt, woher die
            # Einheit stammt, und deckt damit den Zirkel der Ziel-Normalisierung auf.
            stufe_label, stufe = belegstufe(cell.get("timepoint") or "", target, artikel)
            belegstufen[stufe] += 1
            if stufe in ("gedruckt", "artikel", "ziel"):
                stufen_klassen[klassifiziere(target, stufe_label)] += 1
                if key in gold and _close(cell["value"], gold[key], 1e-6, 0.0):
                    if stufe == "ziel":
                        treffer_nur_ziel += 1
                    else:
                        treffer_belegt += 1
            else:
                stufen_klassen["unklar"] += 1
            if label_status == "unklar":
                zaehler["unklar_zellen"] += 1
                if len(unklar_beispiele) < 20:
                    unklar_beispiele.append(
                        {
                            "record_id": record_id,
                            "field": cell["field"],
                            "roh": cell.get("timepoint"),
                            "ziel": (record.get("timepoint") or {}).get("target"),
                        }
                    )
                continue
            # Drei getrennte Faelle: Record ohne Annotation, Zelle ohne
            # Zeitpunktangabe und Zelle mit abweichendem Zeitpunkt.
            art = klassifiziere(target, label)
            zaehler[f"{art}_zellen"] += 1
            pro_feld[cell["field"]][f"{art}_zellen"] += 1
            if key in gold:
                gesehen.add(key)
                if _close(cell["value"], gold[key], 1e-6, 0.0):
                    zaehler[f"{art}_richtig"] += 1
                    pro_feld[cell["field"]][f"{art}_richtig"] += 1
                else:
                    zaehler[f"{art}_falsch"] += 1
            else:
                zaehler[f"{art}_ohne_gold"] += 1
            if art == "rueckfall":
                ziel_rang, label_rang = rang(target), rang(label)
                if ziel_rang is not None and label_rang is not None:
                    distanzen.append(abs(label_rang - ziel_rang))
                if len(rueckfall_beispiele) < 20:
                    rueckfall_beispiele.append(
                        {
                            "record_id": record_id,
                            "field": cell["field"],
                            "target": (record.get("timepoint") or {}).get("target"),
                            "timepoint": cell.get("timepoint"),
                            "value": cell["value"],
                            "gold": gold.get(key),
                        }
                    )
        klasse = arm_klasse(
            cells, [wert for feld, wert in gold.items() if "mean" in feld[0]], artikel, target, record_id
        )
        arm_klassen[klasse] += 1
        if klasse != "arm_konsistent":
            zaehler["records_arm_gemischt"] += 1
            if len(arm_gemischt) < 20:
                arm_gemischt.append(record_id)
            if len(arm_kandidaten) < 20:
                arm_kandidaten.append({"record_id": record_id, "klasse": klasse})
            # Zellebene: Zellen, deren Label vom haeufigsten Label des Records abweicht.
            labels = [normalisiere(c.get("timepoint") or "") for c in cells]
            labels = [l for l in labels if l and l not in ("not applicable", "running text", "not stated")]
            if labels:
                haeufig = Counter(labels).most_common(1)[0][0]
                gemischte_zellen += sum(1 for l in labels if l != haeufig)
                zellen_mit_label += len(labels)
        for key in gold:
            if key not in gesehen:
                fehlend[key[0]] += 1
                zaehler["auslassungen"] += 1

    gesamt = evaluate_numeric(records, predictions)
    gold_cells = sum(len(record["gold"]["cells"]) for record in records)
    ergebnis = {
        "run": args.run,
        "records": len(records),
        "gesamt": gesamt,
        "ohne_ziel": {
            "zellen": zaehler["ohne_ziel_zellen"],
            "richtig": zaehler["ohne_ziel_richtig"],
            "falsch": zaehler["ohne_ziel_falsch"],
            "ohne_gold": zaehler["ohne_ziel_ohne_gold"],
        },
        "ohne_zeitpunkt": {
            "zellen": zaehler["ohne_zeitpunkt_zellen"],
            "richtig": zaehler["ohne_zeitpunkt_richtig"],
            "falsch": zaehler["ohne_zeitpunkt_falsch"],
            "ohne_gold": zaehler["ohne_zeitpunkt_ohne_gold"],
        },
        "zieltreu": {
            "zellen": zaehler["zieltreu_zellen"],
            "richtig": zaehler["zieltreu_richtig"],
            "falsch": zaehler["zieltreu_falsch"],
            "ohne_gold": zaehler["zieltreu_ohne_gold"],
            "precision": round(
                _safe_div(zaehler["zieltreu_richtig"], zaehler["zieltreu_richtig"] + zaehler["zieltreu_falsch"]), 4
            ),
        },
        "rueckfall": {
            "zellen": zaehler["rueckfall_zellen"],
            "richtig": zaehler["rueckfall_richtig"],
            "falsch": zaehler["rueckfall_falsch"],
            "ohne_gold": zaehler["rueckfall_ohne_gold"],
            "precision": round(
                _safe_div(zaehler["rueckfall_richtig"], zaehler["rueckfall_richtig"] + zaehler["rueckfall_falsch"]), 4
            ),
            "zeitdistanz_median_monate": round(sorted(distanzen)[len(distanzen) // 2], 2) if distanzen else None,
            "zeitdistanz_bekannt": len(distanzen),
            "beispiele": rueckfall_beispiele,
        },
        "unklar": {
            "zellen": zaehler["unklar_zellen"],
            "anteil": round(_safe_div(zaehler["unklar_zellen"], gold_cells), 4),
            "beispiele": unklar_beispiele,
        },
        "arm_gemischt": {
            "records": zaehler["records_arm_gemischt"],
            "beispiele": arm_gemischt,
        },
        "belegstufen": {
            "stufen": dict(belegstufen),
            "klassen": dict(stufen_klassen),
            "treffer_belegt": treffer_belegt,
            "treffer_nur_ziel": treffer_nur_ziel,
            "rueckfall_intervall": rueckfall_intervall(dict(stufen_klassen)),
        },
        "arm_klassen": {
            "records": dict(arm_klassen),
            "beispiele": arm_kandidaten,
            "gemischte_zellen": gemischte_zellen,
            "zellen_mit_label": zellen_mit_label,
            "anteil": round(_safe_div(gemischte_zellen, zellen_mit_label), 4) if zellen_mit_label else None,
            "wilson_95_records": wilson(
                sum(anzahl for name, anzahl in arm_klassen.items() if name != "arm_konsistent"),
                sum(arm_klassen.values()),
            ),
            "wilson_95_zellen": wilson(gemischte_zellen, zellen_mit_label),
        },
        "auslassungen": {
            "gesamt": zaehler["auslassungen"],
            "je_feld": dict(sorted(fehlend.items())),
            "quote": round(_safe_div(zaehler["auslassungen"], gold_cells), 4),
        },
        "je_feld": {field: dict(counts) for field, counts in sorted(pro_feld.items())},
        "zell_f1_aus_klassen": round(
            _f1(
                _safe_div(
                    zaehler["zieltreu_richtig"] + zaehler["rueckfall_richtig"],
                    zaehler["zieltreu_richtig"] + zaehler["zieltreu_falsch"]
                    + zaehler["rueckfall_richtig"] + zaehler["rueckfall_falsch"]
                    + zaehler["zieltreu_ohne_gold"] + zaehler["rueckfall_ohne_gold"],
                ),
                _safe_div(zaehler["zieltreu_richtig"] + zaehler["rueckfall_richtig"], gold_cells),
            ),
            4,
        ),
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"[gesamt] F1 {gesamt['cell_f1']:.4f} recall {gesamt['cell_recall']:.4f} precision "
        f"{gesamt['cell_precision']:.4f} MAE {gesamt['mae_pairs']} coverage {gesamt['mae_coverage']} "
        f"({gesamt['mae_pairs_covered']}/{gold_cells}) exakt {gesamt['record_exact']}/{len(records)}"
    )
    for art in ("zieltreu", "rueckfall", "ohne_zeitpunkt", "ohne_ziel"):
        block = ergebnis[art]
        precision = block.get("precision")
        zusatz = f", Precision {precision}" if precision is not None else ""
        print(
            f"[{art}] {block['zellen']} Zellen, richtig {block['richtig']}, falsch {block['falsch']}, "
            f"ohne Gold {block['ohne_gold']}{zusatz}"
        )
    if ergebnis["rueckfall"]["beispiele"]:
        print(f"[rueckfall] Zeitdistanz Median {ergebnis['rueckfall']['zeitdistanz_median_monate']} Monate "
              f"({ergebnis['rueckfall']['zeitdistanz_bekannt']} bestimmbar)")
    print(f"[auslassungen] {ergebnis['auslassungen']}")
    stufen = ergebnis["belegstufen"]
    print(
        f"[belegstufen] {stufen['stufen']} | Rueckfall {stufen['rueckfall_intervall']['untere_grenze']}"
        f"-{stufen['rueckfall_intervall']['obere_grenze']} | Treffer belegt {stufen['treffer_belegt']},"
        f" nur aus Ziel {stufen['treffer_nur_ziel']}"
    )
    arme = ergebnis["arm_klassen"]
    print(
        f"[arme] {arme['records']} | gemischte Zellen {arme['gemischte_zellen']}/{arme['zellen_mit_label']}"
        f" ({arme['anteil']}), Wilson Records {arme['wilson_95_records']}, Zellen {arme['wilson_95_zellen']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
