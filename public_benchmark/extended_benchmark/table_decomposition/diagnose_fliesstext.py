"""Offline-Messung Sprint 48: Zahlen aus dem Fliesstext als Fundstelle.

Frage: Werden die fuenf noch offenen `population_mismatch`-Felder erreichbar
und wertgleich, wenn der gedruckte Fliesstext als Fundstelle zaehlt - ohne
Armumkehr und ohne Gold in der Regel?

Gemessen wird derselbe Stand wie in Sprint 47 (Tabellenwahl aus dem Dokument),
einmal ohne und einmal mit den Fliesstext-Fundstellen aus
`research_agent.table_decomposition.fliesstext`. Die Regeln dort lesen nur
gedruckte Formen:

* ``placebo, n = 28`` (Arm direkt an der Zahl),
* ``(283, 289, and 204 patients received ..., respectively)`` mit genannter
  Population,
* ``5.1% (4/79) ... respectively`` (Zaehler = Ereignisse, Nenner = Groesse).

Zwei Kennzahlen:

* **wertgleich** - irgendeine Fundstelle trifft den Goldwert (bisherige Zahl,
  94/68). Sie zaehlt ein Feld auch dann, wenn daneben eine zweite, abweichende
  Zahl gedruckt steht.
* **streng** - im Feld steht **genau eine** gedruckte Zahl und sie trifft den
  Goldwert. Das ist die Kennzahl, die eine Mehrdeutigkeit nicht verdeckt:
  ein Feld mit zwei Populationen ist wertgleich, aber nicht streng.

Zusaetzlich wird ausgewiesen, wie viele vorher eindeutige Felder der Text
mehrdeutig macht (streng vorher, nicht streng nachher) - die Differenz
101/83 darf diese Regression nicht verdecken.

Read-only: Gold und eingefrorene Eingaben werden nur gelesen.
Aufruf:

    python public_benchmark/extended_benchmark/table_decomposition/diagnose_fliesstext.py \
        --out public_benchmark/extended_benchmark/analysis/.../messung.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

HIER = Path(__file__).resolve()
BENCH = HIER.parent.parent
REPO = BENCH.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(HIER.parent) not in sys.path:
    sys.path.insert(0, str(HIER.parent))

import run_benchmark as rb  # noqa: E402

from research_agent.table_decomposition import fliesstext as fl  # noqa: E402
from research_agent.table_decomposition import provenienz as pv  # noqa: E402
from research_agent.table_decomposition import tabellenwahl as tw  # noqa: E402

from diagnose_populationswahl import _dokument, _gold, _lage  # noqa: E402

SPRINT45 = (BENCH / "analysis" / "table_decomposition_20261118"
            / "provenienz_20261118" / "messung.json")


def _kategorien() -> Dict[tuple, str]:
    if not SPRINT45.exists():
        return {}
    alt = json.loads(SPRINT45.read_text(encoding="utf-8"))
    return {(f["record_id"], f["feld"]): f["kategorie"]
            for f in alt.get("nicht_wertgleich") or []}


def _zusammengelegt(*quellen: Dict[str, List[pv.Provenienz]]
                    ) -> Dict[str, List[pv.Provenienz]]:
    out: Dict[str, List[pv.Provenienz]] = {}
    for quelle in quellen:
        for feld, stellen in quelle.items():
            out.setdefault(feld, []).extend(stellen)
    return out


def _werte(stellen: List[pv.Provenienz]) -> List[float]:
    """Gedruckte Zahlen eines Feldes, entdoppelt und sortiert."""
    return sorted({round(stelle.wert, 2) for stelle in stellen
                   if stelle.wert is not None})


def _streng(lage: Dict[str, Any], werte: List[float]) -> bool:
    """Genau eine gedruckte Zahl, und sie trifft den Goldwert."""
    return bool(lage.get("wertgleich")) and len(werte) == 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--selection", type=Path, default=rb.DEFAULT_SELECTION)
    args = parser.parse_args()

    kategorien = _kategorien()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    records = rb.load_records(rb.DEFAULT_RECORDS)
    grouped = rb.group_by_record(selection, None)

    ohne_erreichbar = ohne_gleich = ohne_streng = 0
    mit_erreichbar = mit_gleich = mit_streng = 0
    ohne_felder: set = set()
    mit_felder: set = set()
    streng_felder: set = set()
    neu_erreichbar: List[str] = []
    verloren: List[str] = []
    streng_verloren: List[Dict[str, Any]] = []
    arm_wechsel: List[Dict[str, Any]] = []
    konflikte: List[Dict[str, Any]] = []
    regeln: Counter = Counter()
    wert_index: Dict[str, List[float]] = {}
    verteilung: Dict[str, Counter] = {"ohne_text": Counter(), "mit_text": Counter()}
    je_kategorie: Dict[str, Dict[str, int]] = {}
    record_berichte: List[Dict[str, Any]] = []

    for record_id, entries in sorted(grouped.items()):
        record = records.get(record_id)
        if record is None:
            continue
        tables, text, _redundant = rb.load_tables(entries, record)
        if not tables:
            continue
        context = rb.context_of(record)
        alle = _dokument(text, str(record["document"]["id"]), context)
        wahl = tw.waehle(tables, alle, context)
        ziel = wahl.tabelle if (wahl and wahl.wechsel) else tables[0]
        gelesen = [ziel] if (wahl and wahl.wechsel) else list(tables)

        tabellen_stellen = pv.feld_stellen(gelesen, context)
        text_stellen = fl.stellen(text, context, gelesen)
        alle_stellen = _zusammengelegt(tabellen_stellen, text_stellen)
        werte_vorher = {feld: _werte(stellen)
                        for feld, stellen in tabellen_stellen.items()}
        werte_nachher = {feld: _werte(stellen)
                         for feld, stellen in alle_stellen.items()}
        gold = _gold(record)
        vorher = _lage(gold, tabellen_stellen)
        nachher = _lage(gold, alle_stellen)
        for feld, werte in werte_nachher.items():
            wert_index[f"{record_id}.{feld}"] = werte

        for feld, stellen in text_stellen.items():
            for stelle in stellen:
                regeln[stelle.regel] += 1
            if not tabellen_stellen.get(feld):
                neu_erreichbar.append(f"{record_id}.{feld}")
            tabellen_werte = set(werte_vorher.get(feld) or [])
            fremd = [wert for wert in werte_nachher.get(feld) or []
                     if wert not in tabellen_werte]
            if tabellen_werte and fremd:
                konflikte.append({"record_id": record_id, "feld": feld,
                                  "tabelle": sorted(tabellen_werte),
                                  "text": fremd})

        for feld in sorted(set(vorher) | set(nachher)):
            schluessel = f"{record_id}.{feld}"
            v = vorher.get(feld) or {"erreichbar": False, "wertgleich": False,
                                     "arme": []}
            n = nachher.get(feld) or {"erreichbar": False, "wertgleich": False,
                                      "arme": []}
            v_werte = werte_vorher.get(feld) or []
            n_werte = werte_nachher.get(feld) or []
            v_streng = _streng(v, v_werte)
            n_streng = _streng(n, n_werte)

            if v.get("erreichbar"):
                ohne_erreichbar += 1
                verteilung["ohne_text"][min(len(v_werte), 3)] += 1
                if v.get("wertgleich"):
                    ohne_gleich += 1
                    ohne_felder.add(schluessel)
                if v_streng:
                    ohne_streng += 1
            if n.get("erreichbar"):
                mit_erreichbar += 1
                verteilung["mit_text"][min(len(n_werte), 3)] += 1
                if n.get("wertgleich"):
                    mit_gleich += 1
                    mit_felder.add(schluessel)
                if n_streng:
                    mit_streng += 1
                    streng_felder.add(schluessel)

            if v.get("erreichbar") and not n.get("erreichbar"):
                verloren.append(schluessel)
                continue
            if not v.get("erreichbar"):
                continue
            if v.get("arme") and n.get("arme") != v.get("arme"):
                arm_wechsel.append({"record_id": record_id, "feld": feld,
                                    "vorher": v.get("arme"),
                                    "nachher": n.get("arme")})
            if v_streng and not n_streng:
                streng_verloren.append({
                    "record_id": record_id, "feld": feld,
                    "vorher": v_werte, "nachher": n_werte,
                    "noch_wertgleich": bool(n.get("wertgleich")),
                })
            kategorie = kategorien.get((record_id, feld))
            if kategorie:
                zaehler = je_kategorie.setdefault(
                    kategorie, {"gesamt": 0, "vorher": 0, "nachher": 0,
                                "streng_vorher": 0, "streng_nachher": 0})
                zaehler["gesamt"] += 1
                zaehler["vorher"] += 1 if v.get("wertgleich") else 0
                zaehler["nachher"] += 1 if n.get("wertgleich") else 0
                zaehler["streng_vorher"] += 1 if v_streng else 0
                zaehler["streng_nachher"] += 1 if n_streng else 0

        record_berichte.append({
            "record_id": record_id,
            "outcome": context.get("outcome"),
            "tabelle": ziel.table_id,
            "fliesstext": {feld: [stelle.to_dict() for stelle in stellen]
                           for feld, stellen in sorted(text_stellen.items())},
            # sortiert, damit die Datei zwischen Laeufen byte-gleich bleibt
            "fundstellen": {feld: werte_nachher[feld]
                            for feld in sorted(alle_stellen)},
            "fundstellen_vorher": {feld: werte_vorher[feld]
                                   for feld in sorted(tabellen_stellen)},
            "vorher": vorher,
            "nachher": nachher,
        })

    bericht = {
        "selection": {
            "pfad": str(args.selection.relative_to(REPO))
                    if args.selection.is_absolute() else str(args.selection),
            "role": selection.get("role"),
            "n_tables": len(selection.get("tables") or []),
            "n_records": len(selection.get("record_ids") or []),
        },
        "bilanz": {
            "ohne_text": {"erreichbar": ohne_erreichbar,
                          "wertgleich": ohne_gleich,
                          "streng": ohne_streng},
            "mit_text": {"erreichbar": mit_erreichbar,
                         "wertgleich": mit_gleich,
                         "streng": mit_streng},
            "neu_wertgleich": sorted(mit_felder - ohne_felder),
            # Ein Feld mit zwei gedruckten Zahlen ist wertgleich, aber nicht
            # eindeutig - das wird getrennt ausgewiesen.
            "neu_wertgleich_eindeutig": [
                feld for feld in sorted(mit_felder - ohne_felder)
                if len(wert_index.get(feld) or []) == 1],
            "neu_wertgleich_mehrdeutig": [
                feld for feld in sorted(mit_felder - ohne_felder)
                if len(wert_index.get(feld) or []) > 1],
            "neu_streng": sorted(streng_felder - ohne_felder),
            "streng_verloren": streng_verloren,
            "verloren": sorted(set(verloren)),
            "arm_wechsel": arm_wechsel,
            "text_fakten": dict(sorted(regeln.items())),
            "konflikte": konflikte,
            "gedruckte_zahlen_je_feld": {
                name: {("3+" if k == 3 else str(k)): v
                       for k, v in sorted(zaehler.items())}
                for name, zaehler in verteilung.items()},
        },
        "felder_nur_aus_text": sorted(set(neu_erreichbar)),
        "je_kategorie": dict(sorted(je_kategorie.items())),
        "records": record_berichte,
    }
    Path(args.out).write_text(
        json.dumps(bericht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    bilanz = bericht["bilanz"]
    ohne, mit = bilanz["ohne_text"], bilanz["mit_text"]
    print(f"ohne Text {ohne['erreichbar']} erreichbar / "
          f"{ohne['wertgleich']} wertgleich / {ohne['streng']} streng")
    print(f"mit Text  {mit['erreichbar']} erreichbar / "
          f"{mit['wertgleich']} wertgleich / {mit['streng']} streng")
    print("je Kategorie:", bericht["je_kategorie"])
    print("neu wertgleich:", len(bilanz["neu_wertgleich"]),
          "(eindeutig", len(bilanz["neu_wertgleich_eindeutig"]),
          "/ mehrdeutig", len(bilanz["neu_wertgleich_mehrdeutig"]), ")",
          "| neu streng:", len(bilanz["neu_streng"]),
          "| streng verloren:", len(bilanz["streng_verloren"]),
          "| verloren:", len(bilanz["verloren"]),
          "| Armwechsel:", len(arm_wechsel))
    print("gedruckte Zahlen je Feld:",
          bilanz["gedruckte_zahlen_je_feld"])
    print("Felder nur aus Text:", len(bericht["felder_nur_aus_text"]))
    print("Text-Fakten:", bilanz["text_fakten"])
    print("Konflikte (Textwert weicht von der Tabelle ab):", len(konflikte))
    for eintrag in bilanz["streng_verloren"]:
        print("  streng verloren:", eintrag["record_id"], eintrag["feld"],
              eintrag["vorher"], "->", eintrag["nachher"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
