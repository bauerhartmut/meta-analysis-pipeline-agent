"""Offline-Messung: was leisten Tabellen mit Zeitpunkten im Spaltenkopf?

Untersucht die ausgewaehlten Tabellen, deren Zeitpunkte nur im Kopf stehen
(``semantics.column_timepoints``), und vergleicht drei Sichten:

1. **heute**: welche Felder und Werte die Tabelle mit dem aktuellen Stand
   hergibt (Rollen, Arme, Transfers, Auswahlregel ``primary_tables``).
2. **je_zeitpunkt**: dieselbe Tabelle auf die Spalten *eines* Zeitpunkts
   reduziert - so, wie eine Auswahlregel ueber ``column_timepoints`` sie
   zuschneiden wuerde. Das kann nur verteilen, was die Tabelle hergibt; es
   erzeugt keine Felder.
3. **auswahl**: was eine um Spaltenzeitpunkte erweiterte ``primary_tables``
   verdraengen wuerde (Schluessel: Zeilenzeitpunkte, sonst Spaltenzeitpunkte),
   verglichen mit der heutigen Verdraengung.

Zusaetzlich je Goldzelle: ist das Feld erreichbar, steht der Wert woertlich in
der Tabelle, und in welcher Zeile/Spalte. Damit trennt die Messung zwei
moegliche Blockaden: fehlende Zeitpunkt-Auswahl gegen fehlende
Rollen-/Outcome-Erkennung.

Read-only: aendert keine Produktionsdatei, kein Gold, keine Messartefakte.
Aufruf:

    python public_benchmark/extended_benchmark/table_decomposition/diagnose_spaltenzeitpunkte.py \
        --out public_benchmark/extended_benchmark/analysis/.../messung.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

HIER = Path(__file__).resolve()
BENCH = HIER.parent.parent
REPO = BENCH.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(HIER.parent) not in sys.path:
    sys.path.insert(0, str(HIER.parent))

import run_benchmark as rb  # noqa: E402

from research_agent.table_decomposition.model import (  # noqa: E402
    ROLE_LABEL,
    ROLE_UNKNOWN,
    Table,
)
from research_agent.table_decomposition.parser import parse_document  # noqa: E402
from research_agent.table_decomposition.semantics import (  # noqa: E402
    _norm_label,
    _timepoint_key,
    cell_arm,
    column_timepoints,
    enrich_table,
    field_for,
    outcome_rows,
    primary_tables,
    reachable_cells,
    reachable_fields,
    transfer_arms_from_document,
    transfer_arms_within_document,
)

DEFAULT_TABLES = ("PMC5777419:T2", "PMC3278655:T2")


_ZAHL_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)?")
# Minus- und Gedankenstriche, die in den Abzuegen als Vorzeichen auftreten.
_MINUS = str.maketrans({"\u2212": "-", "\u2013": "-", "\u2014": "-"})


def _zahl_paare(text: str) -> List[Tuple[float, str]]:
    """Alle Zahlen einer Zelle als (Wert, gedrucktes Zeichen).

    Dezimalkomma wird zum Punkt, Unicode-Minus zum ASCII-Minus; Fussnotenzeichen
    (``[\u2020](#)``, ``[*](#)``) fallen weg, weil sie nicht im Zahlmuster stehen.
    Eine Zelle wie ``4.1 \u00b11.0`` oder ``--0.38 (0.37)`` liefert damit **beide**
    Werte - Mittel und Streuung -, sodass der Vergleich nicht an der Verbundzelle
    scheitert. ``1`` und ``1.0`` sind derselbe Wert; das gedruckte Zeichen bleibt
    erhalten, damit eine Null nicht mit jedem Dezimalnullwert gleichgesetzt wird.
    """
    paare: List[Tuple[float, str]] = []
    for treffer in _ZAHL_RE.findall((text or "").translate(_MINUS)):
        try:
            paare.append((float(treffer.replace(",", ".")), treffer))
        except ValueError:
            continue
    return paare


def _zahlen(text: str) -> List[float]:
    """Nur die Werte aus ``_zahl_paare``."""
    return [wert for wert, _zeichen in _zahl_paare(text)]


def _gleich(a: float, b: float) -> bool:
    """Gleicher Wert trotz Schreibweise (``1`` gegen ``1.0``)."""
    return abs(a - b) <= 1e-9 * max(1.0, abs(b))


def _zelltreffer(text: str, soll: float) -> bool:
    """Steht ``soll`` in dieser Zelle?

    Sonderfall Null: eine Ereigniszahl ``0`` darf nicht in jeder Zelle mit
    Dezimalnull (``0.00``, ``--0.00``) "gefunden" werden - sonst behauptet die
    Messung einen gedruckten Wert, der dort nicht steht.
    """
    for wert, zeichen in _zahl_paare(text):
        if not _gleich(wert, soll):
            continue
        if soll == 0 and ("." in zeichen or "," in zeichen):
            continue
        return True
    return False


def _spaltenfeld(column, row) -> Optional[str]:
    """Feld, das eine einzelne Spalte in dieser Zeile belegt.

    Spiegelt die Zweige aus ``semantics.row_fields`` - die Messung zaehlt
    dieselben Spalten wie die Produktion, nur eben einzeln, damit sich Werte
    einem Zeitpunkt zuordnen lassen.
    """
    cell = row.cells.get(column.col_id)
    text = (cell.text or "") if cell is not None else ""
    if not text.strip():
        return None
    arm = cell_arm(column, row)
    if column.field:
        return column.field
    role = getattr(row, "value_role", "")
    if column.role == ROLE_UNKNOWN and role:
        return field_for(role, arm)
    if column.is_outcome and column.role != ROLE_UNKNOWN:
        return field_for(column.role, arm)
    return None


def _kandidaten(table: Table, context: Dict[str, Any],
                col_ids: Optional[Iterable[int]] = None) -> List[Dict[str, Any]]:
    """Alle (Feld, Wert)-Kandidaten der Outcome-Zeilen, optional je Spaltensatz."""
    wanted = set(col_ids) if col_ids is not None else None
    rows = outcome_rows(table, str(context.get("outcome") or ""))
    kandidaten: List[Dict[str, Any]] = []
    for row_id in rows:
        row = table.row(row_id)
        if row is None:
            continue
        for column in table.columns:
            if column.role == ROLE_LABEL:
                continue
            if wanted is not None and column.col_id not in wanted:
                continue
            field = _spaltenfeld(column, row)
            if not field:
                continue
            cell = row.cells.get(column.col_id)
            kandidaten.append({
                "field": field,
                "wert": (cell.text or "").strip() if cell is not None else "",
                "zeile": f"r{row_id}",
                "spalte": f"c{column.col_id}",
                "arm": cell_arm(column, row),
                "zeitpunkt": _spaltenzeitpunkt(table, column),
            })
    return kandidaten


def _spaltenzeitpunkt(table: Table, column) -> Optional[str]:
    """Zeitpunkt dieses Spaltenkopfs, falls einer der erkannten ist."""
    labels = {_norm_label(name) for name in column_timepoints(table)}
    for teil in column.header_path or ():
        name = _norm_label(teil)
        if name in labels:
            return name
    return None


def _kopffakten(table: Table, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Kopfangaben (``n = ...``) im Feldformat von ``reachable_cells``."""
    fakten = []
    for fact in table.header_facts:
        arm = fact.get("arm")
        field = field_for("n", arm if isinstance(arm, str) else None)
        if field:
            fakten.append({"field": field, "wert": fact.get("value"), "arm": arm,
                           "spalte": f"c{fact.get('col_start')}"})
    return fakten


def _verdraengung(tables: Sequence[Table],
                  context: Dict[str, Any]) -> Dict[str, str]:
    """Heutige Auswahlregel als Zuordnung ``verdraengt -> gewaehlt``."""
    return primary_tables(tables, context)


def _verdraengung_mit_spaltenzeitpunkten(tables: Sequence[Table],
                                         context: Dict[str, Any]) -> Dict[str, str]:
    """Dieselbe Regel, aber Spaltenzeitpunkte zaehlen als Zeitpunktgruppe.

    Bewusst hier nachgebaut statt in der Produktion verdrahtet: die Messung
    soll den Unterschied zeigen, ohne die eingefrorene Messung zu verschieben.
    """
    def served(table: Table) -> set:
        return {name for _row_id, name in reachable_cells(table, context)}

    def key(table: Table) -> Tuple[str, ...]:
        return _timepoint_key(table) or column_timepoints(table)

    gruppen: Dict[Tuple[str, ...], List[Table]] = {}
    for table in tables:
        schluessel = key(table)
        if not schluessel or not served(table):
            continue
        gruppen.setdefault(schluessel, []).append(table)
    redundant: Dict[str, str] = {}
    for gruppe in gruppen.values():
        if len(gruppe) < 2:
            continue
        geordnet = sorted(gruppe, key=lambda t: (t.index, t.table_id))
        erste = geordnet[0]
        felder = served(erste)
        if not all(served(t) <= felder for t in geordnet[1:]):
            continue
        for table in geordnet[1:]:
            redundant[table.table_id] = erste.table_id
    return redundant


def _gold_abgleich(table: Table, record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Je Goldzelle: erreichbar? Wert woertlich in der Tabelle?"""
    context = rb.context_of(record)
    felder = {name for _row_id, name in reachable_cells(table, context)}
    ergebnis = []
    for cell in record["gold"]["cells"]:
        wert = cell.get("raw")
        treffer = []
        soll = _zahlen(str(wert)) if wert is not None else []
        for row in table.rows:
            for column in table.columns:
                zelle = row.cells.get(column.col_id)
                if zelle is None or not soll:
                    continue
                if _zelltreffer(zelle.text or "", soll[0]):
                    treffer.append(f"r{row.row_id}/c{column.col_id}")
        # Stichprobengroessen stehen in Kopfbändern (``(n=16)``), nicht in
        # Zellen; ohne diesen Blick meldet die Messung "nicht gedruckt", obwohl
        # der Wert dasteht - nur ohne zugeordneten Arm.
        for band in table.header_bands:
            if _zelltreffer(band.text or "", soll[0]):
                treffer.append(f"band:L{band.level}c{band.col_start}")
        ergebnis.append({
            "field": cell["field"],
            "wert": cell.get("raw"),
            "erreichbar": cell["field"] in felder,
            "wert_gedruckt_in": treffer,
        })
    return ergebnis


def messe(selection: Dict[str, Any], records: Dict[str, Dict[str, Any]],
          table_ids: Sequence[str]) -> Dict[str, Any]:
    ergebnisse: List[Dict[str, Any]] = []
    for entry in selection["tables"]:
        if table_ids and entry["table_id"] not in table_ids:
            continue
        for record_id in entry["record_ids"]:
            record = records.get(record_id)
            if record is None:
                continue
            pfad = rb.REPO / entry["document_path"]
            text = pfad.read_text(encoding="utf-8", errors="replace")
            doc_id = str(record["document"].get("id") or pfad.stem)
            parsed = parse_document(text, doc_id)
            context = rb.context_of(record)
            for tabelle in parsed.tables:
                enrich_table(tabelle, context)
            transfer_arms_within_document(parsed.tables, context)
            transfer_arms_from_document(parsed.tables, context, text)
            heutige_auswahl = _verdraengung(parsed.tables, context)
            neue_auswahl = _verdraengung_mit_spaltenzeitpunkten(parsed.tables, context)
            tabelle = next((t for t in parsed.tables
                            if t.table_id == entry["table_id"]), None)
            if tabelle is None:
                continue
            felder = reachable_fields(tabelle)
            kopf = _kopffakten(tabelle, context)
            heute = _kandidaten(tabelle, context)
            zellen = sorted(reachable_cells(tabelle, context))
            assert {name for _row_id, name in zellen} == (
                {k["field"] for k in heute} | {k["field"] for k in kopf}
            ), "Messung weicht von reachable_cells ab"

            zeitpunkte = column_timepoints(tabelle)
            je_zeitpunkt: List[Dict[str, Any]] = []
            for zeitpunkt in zeitpunkte:
                spalten = [c.col_id for c in tabelle.columns
                           if _spaltenzeitpunkt(tabelle, c) == zeitpunkt]
                je_zeitpunkt.append({
                    "zeitpunkt": zeitpunkt,
                    "spalten": [f"c{c}" for c in spalten],
                    "felder": sorted({k["field"] for k in _kandidaten(
                        tabelle, context, spalten)}),
                    "kandidaten": _kandidaten(tabelle, context, spalten),
                })
            ergebnisse.append({
                "table_id": entry["table_id"],
                "record_id": record_id,
                "outcome": context.get("outcome"),
                "zeitpunkt_ziel": context.get("timepoint_target"),
                "zeilenzeitpunkte": list(_timepoint_key(tabelle)),
                "spaltenzeitpunkte": list(zeitpunkte),
                "outcome_zeilen": outcome_rows(tabelle, str(context.get("outcome") or "")),
                "zeilen_gesamt": len(tabelle.rows),
                "spalten_gesamt": len(tabelle.columns),
                "spalten_mit_feld": [f"c{c.col_id}:{c.field}" for c in tabelle.columns
                                     if c.field],
                "reachable_fields": sorted(felder),
                "heute_kandidaten": heute,
                "heute_kopfangaben": kopf,
                "je_zeitpunkt": je_zeitpunkt,
                "auswahl_heute": {k: v for k, v in heutige_auswahl.items()},
                "auswahl_mit_spaltenzeitpunkten": neue_auswahl,
                "gold": _gold_abgleich(tabelle, record),
            })
    return {
        "tables": list(table_ids),
        "ergebnisse": ergebnisse,
        "summe": _summe(ergebnisse),
    }


def _summe(ergebnisse: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    felder_heute = 0
    felder_je_zeitpunkt = 0
    gold_gesamt = 0
    gold_feld = 0
    gold_wert = 0
    mehrfach = 0
    neue_verdraengung = 0
    for eintrag in ergebnisse:
        felder_heute += len({k["field"] for k in eintrag["heute_kandidaten"]}
                            | {k["field"] for k in eintrag["heute_kopfangaben"]})
        felder_je_zeitpunkt += len({k["field"] for block in eintrag["je_zeitpunkt"]
                                    for k in block["kandidaten"]})
        if eintrag["auswahl_heute"] != eintrag["auswahl_mit_spaltenzeitpunkten"]:
            neue_verdraengung += 1
        for kandidat in eintrag["heute_kandidaten"]:
            if sum(1 for k in eintrag["heute_kandidaten"]
                   if k["field"] == kandidat["field"]) > 1:
                mehrfach += 1
                break
        for zelle in eintrag["gold"]:
            gold_gesamt += 1
            gold_feld += 1 if zelle["erreichbar"] else 0
            gold_wert += 1 if zelle["wert_gedruckt_in"] else 0
    return {
        "tabellen_record_paare": len(ergebnisse),
        "felder_heute": felder_heute,
        "felder_je_zeitpunkt_summe": felder_je_zeitpunkt,
        "tabellen_mit_mehrfachkandidat": mehrfach,
        "tabellen_mit_neuer_verdraengung": neue_verdraengung,
        "goldzellen": gold_gesamt,
        "goldzellen_feld_erreichbar": gold_feld,
        "goldzellen_wert_gedruckt": gold_wert,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=rb.DEFAULT_SELECTION)
    parser.add_argument("--records", type=Path, default=rb.DEFAULT_RECORDS)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--table", action="append", default=None,
                        help="nur diese Tabelle(n); mehrfach angebbar")
    args = parser.parse_args(argv)

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    records = rb.load_records(args.records)
    ergebnis = messe(selection, records, args.table or DEFAULT_TABLES)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    for eintrag in ergebnis["ergebnisse"]:
        felder = sorted({k["field"] for k in eintrag["heute_kandidaten"]}
                        | {k["field"] for k in eintrag["heute_kopfangaben"]})
        print(f"{eintrag['table_id']} ({eintrag['record_id']}): "
              f"Zeitpunkte={len(eintrag['spaltenzeitpunkte'])} "
              f"Felder heute={felder} Gold={len(eintrag['gold'])}")
    print("Summe:", ergebnis["summe"])
    print("geschrieben:", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
