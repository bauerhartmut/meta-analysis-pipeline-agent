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

Drei Kennzahlen:

* **wertgleich** - irgendeine Fundstelle trifft den Goldwert, auch wenn daneben
  eine zweite, abweichende Zahl gedruckt steht (94/68).
* **streng** - genau eine gedruckte Zahl im Feld **und** das Feld ist
  wertgleich (bisherige strenge Kennzahl; die Eindeutigkeit haengt damit an
  `wertgleich`).
* **streng_direkt** - genau eine gedruckte Zahl im Feld und **diese Zahl**
  trifft den Goldwert (Vergleich Zahl gegen Gold, ohne Umweg ueber
  `wertgleich`).

Dazu die **Korroboration aus dem Ergebnissatz**: steht die Zahl als
``n = X`` in einem Satz, der das Outcome nennt, ist sie fuer die
Analyspopulation belegt. ``streng_gewaehlt`` waehlt je Feld die belegten Zahlen
(sonst alle) und prueft, ob genau eine uebrig bleibt und sie den Goldwert
trifft.

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
from typing import Any, Dict, List, Optional

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


def _belegte_werte(stellen: List[pv.Provenienz]) -> List[float]:
    """Gedruckte Zahlen, die im Ergebnissatz als ``n = X`` stehen."""
    return sorted({round(stelle.wert, 2) for stelle in stellen
                   if stelle.wert is not None and getattr(stelle, "belegt", False)})


def _gleich_zahl(wert: float, gold: Optional[float]) -> bool:
    """Zahl gegen Gold, ohne Umweg ueber eine Fundstellenpruefung."""
    return gold is not None and abs(wert - gold) <= 1e-9 * max(1.0, abs(gold))


def _streng_wertgleich(lage: Dict[str, Any], werte: List[float]) -> bool:
    """Bisherige strenge Kennzahl: eine Zahl, Feld wertgleich."""
    return bool(lage.get("wertgleich")) and len(werte) == 1


def _streng_direkt(werte: List[float], gold: Optional[float]) -> bool:
    """Strenge Kennzahl neu: eine Zahl, und diese Zahl trifft Gold."""
    return len(werte) == 1 and _gleich_zahl(werte[0], gold)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--selection", type=Path, default=rb.DEFAULT_SELECTION)
    args = parser.parse_args()

    kategorien = _kategorien()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    records = rb.load_records(rb.DEFAULT_RECORDS)
    grouped = rb.group_by_record(selection, None)

    zaehler_ohne = Counter()
    zaehler_mit = Counter()
    zaehler_gewaehlt = Counter()
    ohne_felder: set = set()
    mit_felder: set = set()
    direkt_felder: set = set()
    gewaehlt_felder: set = set()
    neu_erreichbar: List[str] = []
    verloren: List[str] = []
    streng_verloren: List[Dict[str, Any]] = []
    direkt_gewonnen: List[str] = []
    direkt_verloren: List[Dict[str, Any]] = []
    korroboriert_aufgeloest: List[Dict[str, Any]] = []
    definition_abweichungen: List[Dict[str, Any]] = []
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
        belegte = {feld: _belegte_werte(stellen)
                   for feld, stellen in alle_stellen.items()}
        gold = _gold(record)
        gold_werte = {zelle["field"]: zelle["value"] for zelle in gold}
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
                                  "text": fremd,
                                  "belegt": belegte.get(feld) or []})

        for feld in sorted(set(vorher) | set(nachher)):
            schluessel = f"{record_id}.{feld}"
            v = vorher.get(feld) or {"erreichbar": False, "wertgleich": False,
                                     "arme": []}
            n = nachher.get(feld) or {"erreichbar": False, "wertgleich": False,
                                      "arme": []}
            v_werte = werte_vorher.get(feld) or []
            n_werte = werte_nachher.get(feld) or []
            gold_wert = gold_werte.get(feld)
            v_direkt = _streng_direkt(v_werte, gold_wert)
            n_direkt = _streng_direkt(n_werte, gold_wert)
            gewaehlt = belegte.get(feld) or n_werte
            n_gewaehlt = len(gewaehlt) == 1 and _gleich_zahl(gewaehlt[0], gold_wert)

            if v.get("erreichbar"):
                zaehler_ohne["erreichbar"] += 1
                verteilung["ohne_text"][min(len(v_werte), 3)] += 1
                if v.get("wertgleich"):
                    zaehler_ohne["wertgleich"] += 1
                    ohne_felder.add(schluessel)
                if _streng_wertgleich(v, v_werte):
                    zaehler_ohne["streng"] += 1
                if v_direkt:
                    zaehler_ohne["streng_direkt"] += 1
            if n.get("erreichbar"):
                zaehler_mit["erreichbar"] += 1
                verteilung["mit_text"][min(len(n_werte), 3)] += 1
                if n.get("wertgleich"):
                    zaehler_mit["wertgleich"] += 1
                    mit_felder.add(schluessel)
                if _streng_wertgleich(n, n_werte):
                    zaehler_mit["streng"] += 1
                if n_direkt:
                    zaehler_mit["streng_direkt"] += 1
                    direkt_felder.add(schluessel)
                if n_gewaehlt:
                    zaehler_mit["streng_gewaehlt"] += 1
                    zaehler_gewaehlt["streng"] += 1
                    gewaehlt_felder.add(schluessel)

            if v.get("erreichbar") and not n.get("erreichbar"):
                verloren.append(schluessel)
                continue
            if not v.get("erreichbar"):
                continue
            if v.get("arme") and n.get("arme") != v.get("arme"):
                arm_wechsel.append({"record_id": record_id, "feld": feld,
                                    "vorher": v.get("arme"),
                                    "nachher": n.get("arme")})
            if _streng_wertgleich(v, v_werte) and not _streng_wertgleich(n, n_werte):
                streng_verloren.append({
                    "record_id": record_id, "feld": feld,
                    "vorher": v_werte, "nachher": n_werte,
                    "noch_wertgleich": bool(n.get("wertgleich")),
                })
            # Wo die beiden strengen Definitionen auseinanderlaufen: eine
            # einzige gedruckte Zahl, wertgleich, aber nicht der Goldwert.
            for phase, lage, werte in (("vorher", v, v_werte),
                                       ("nachher", n, n_werte)):
                if (lage.get("wertgleich") and len(werte) == 1
                        and not _gleich_zahl(werte[0], gold_wert)):
                    definition_abweichungen.append({
                        "record_id": record_id, "feld": feld, "phase": phase,
                        "zahl": werte[0], "gold": gold_wert})
            if v_direkt and not n_direkt:
                direkt_verloren.append({
                    "record_id": record_id, "feld": feld, "gold": gold_wert,
                    "vorher": v_werte, "nachher": n_werte,
                })
            if not v_direkt and n_direkt:
                direkt_gewonnen.append(schluessel)
            if belegte.get(feld) and len(n_werte) > 1 and n_gewaehlt:
                korroboriert_aufgeloest.append({
                    "record_id": record_id, "feld": feld, "gold": gold_wert,
                    "alle": n_werte, "belegt": belegte[feld],
                })
            kategorie = kategorien.get((record_id, feld))
            if kategorie:
                eintrag = je_kategorie.setdefault(
                    kategorie, {"gesamt": 0, "vorher": 0, "nachher": 0,
                                "streng_vorher": 0, "streng_nachher": 0,
                                "streng_direkt_vorher": 0,
                                "streng_direkt_nachher": 0,
                                "streng_gewaehlt": 0})
                eintrag["gesamt"] += 1
                eintrag["vorher"] += 1 if v.get("wertgleich") else 0
                eintrag["nachher"] += 1 if n.get("wertgleich") else 0
                eintrag["streng_vorher"] += 1 if _streng_wertgleich(v, v_werte) else 0
                eintrag["streng_nachher"] += 1 if _streng_wertgleich(n, n_werte) else 0
                eintrag["streng_direkt_vorher"] += 1 if v_direkt else 0
                eintrag["streng_direkt_nachher"] += 1 if n_direkt else 0
                eintrag["streng_gewaehlt"] += 1 if n_gewaehlt else 0

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
            "belegt": {feld: belegte[feld] for feld in sorted(belegte)
                       if belegte[feld]},
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
            "ohne_text": dict(zaehler_ohne),
            "mit_text": dict(zaehler_mit),
            "neu_wertgleich": sorted(mit_felder - ohne_felder),
            # Ein Feld mit zwei gedruckten Zahlen ist wertgleich, aber nicht
            # eindeutig - das wird getrennt ausgewiesen.
            "neu_wertgleich_eindeutig": [
                feld for feld in sorted(mit_felder - ohne_felder)
                if len(wert_index.get(feld) or []) == 1],
            "neu_wertgleich_mehrdeutig": [
                feld for feld in sorted(mit_felder - ohne_felder)
                if len(wert_index.get(feld) or []) > 1],
            "neu_streng": sorted(gewaehlt_felder - ohne_felder),
            "streng_verloren": streng_verloren,
            "streng_direkt_gewonnen": direkt_gewonnen,
            "streng_direkt_verloren": direkt_verloren,
            "streng_direkt_differenz": (
                zaehler_mit["streng_direkt"] - zaehler_ohne["streng_direkt"]),
            # Leer heisst: beide strengen Definitionen stimmen auf dieser
            # Auswahl ueberein - keine einzige Zahl weicht bei einem Feld mit
            # genau einer Zahl vom Goldwert ab.
            "definition_abweichungen": definition_abweichungen,
            "korroboration": {
                "felder_mit_belegter_zahl": len({
                    f"{r['record_id']}.{feld}" for r in record_berichte
                    for feld in r["belegt"]}),
                "mehrdeutig_aufgeloest": korroboriert_aufgeloest,
            },
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
    print(f"ohne Text {ohne['erreichbar']} erreichbar / {ohne['wertgleich']} "
          f"wertgleich / {ohne.get('streng', 0)} streng / "
          f"{ohne.get('streng_direkt', 0)} streng_direkt")
    print(f"mit Text  {mit['erreichbar']} erreichbar / {mit['wertgleich']} "
          f"wertgleich / {mit.get('streng', 0)} streng / "
          f"{mit.get('streng_direkt', 0)} streng_direkt / "
          f"{mit.get('streng_gewaehlt', 0)} streng_gewaehlt")
    print("je Kategorie:", bericht["je_kategorie"])
    print("neu wertgleich:", len(bilanz["neu_wertgleich"]),
          "(eindeutig", len(bilanz["neu_wertgleich_eindeutig"]),
          "/ mehrdeutig", len(bilanz["neu_wertgleich_mehrdeutig"]), ")",
          "| streng_direkt gewonnen:", len(direkt_gewonnen),
          "| verloren:", len(direkt_verloren),
          "| Armwechsel:", len(arm_wechsel))
    print("gedruckte Zahlen je Feld:", bilanz["gedruckte_zahlen_je_feld"])
    print("Korroboration:", bilanz["korroboration"]["felder_mit_belegter_zahl"],
          "Felder mit belegter Zahl, davon mehrdeutig aufgeloest:",
          len(korroboriert_aufgeloest))
    for eintrag in korroboriert_aufgeloest:
        print("  ", eintrag)
    print("Felder nur aus Text:", len(bericht["felder_nur_aus_text"]))
    print("Text-Fakten:", bilanz["text_fakten"])
    print("Konflikte:", len(konflikte))
    for eintrag in direkt_verloren:
        print("  streng_direkt verloren:", eintrag["record_id"], eintrag["feld"],
              eintrag["vorher"], "->", eintrag["nachher"], "| gold", eintrag["gold"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
