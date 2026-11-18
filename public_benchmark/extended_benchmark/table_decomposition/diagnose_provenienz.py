"""Offline-Messung Sprint 45: Provenienz und Fehlerklassen der Goldfelder.

Beantwortet drei Fragen, ohne Gold zur Steuerung der Extraktion zu verwenden:

1. Woher stammt jedes erreichbare Goldfeld? ``research_agent.provenienz``
   beschreibt Fundstelle, Originaltext, Arm, Zeitpunkt, Regel und Sicherheit
   und trennt direkt gedruckte von abgeleiteten Werten.
2. Warum sind 36 der 94 erreichbaren Felder nicht wertgleich? Jedes Feld
   bekommt genau eine Klasse - aber nur, wenn ein Beleg sie traegt: die
   Zitatstelle muss im Dokument stehen, die Summe muss aufgehen, oder der Wert
   muss an einer anderen Stelle derselben Tabelle gedruckt sein. Sonst bleibt
   es ``unexplained``.
3. Vollstaendige Belege der beiden Armkonflikte (PMC5617873, PMC5777419).

Read-only: Gold und eingefrorene Eingaben werden gelesen, nicht geschrieben.
Aufruf:

    python public_benchmark/extended_benchmark/table_decomposition/diagnose_provenienz.py \
        --out public_benchmark/extended_benchmark/analysis/.../messung.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

HIER = Path(__file__).resolve()
BENCH = HIER.parent.parent
REPO = BENCH.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(HIER.parent) not in sys.path:
    sys.path.insert(0, str(HIER.parent))

import run_benchmark as rb  # noqa: E402

from research_agent.table_decomposition import provenienz as pv  # noqa: E402
from research_agent.table_decomposition.model import ROLE_N  # noqa: E402
from research_agent.table_decomposition.parser import parse_document  # noqa: E402
from research_agent.table_decomposition.semantics import (  # noqa: E402
    enrich_table,
    field_for,
    reachable_cells,
    transfer_arms_from_document,
    transfer_arms_within_document,
)

from diagnose_spaltenzeitpunkte import _zelltreffer  # noqa: E402

EXACT = "exact_value"
SUMME = "sum_of_subgroups"
UNTERGRUPPE = "subgroup_vs_total"
POPULATION = "population_mismatch"
ZEITPUNKT = "timepoint_mismatch"
UNERKLAERT = "unexplained"

# Je (record_id, feld, goldwert): Klasse und Beleg. Der Beleg wird geprueft -
# Zitat im Dokument, Summe der Kopfangaben oder Wert an anderer Stelle.
BELEGE: Dict[Tuple[str, str, str], Dict[str, str]] = {
    # --- Summe gedruckter Untergruppen -------------------------------------
    ("yun2024:172", "intervention_group_size", "33"): {
        "kategorie": SUMME,
        "befund": "Metformin 17 + Sitagliptin 16; im Dokument steht keine "
                  "gedruckte Gruppengroesse 33.",
    },
    ("yun2024:174", "intervention_group_size", "33"): {
        "kategorie": SUMME,
        "befund": "Metformin 17 + Sitagliptin 16; im Dokument steht keine "
                  "gedruckte Gruppengroesse 33.",
    },
    ("yun2024:662", "intervention_group_size", "37"): {
        "kategorie": SUMME,
        "befund": "Metformin 21 + Pioglitazon 16; das Dokument nennt 21 und 16, "
                  "keine Summe 37.",
        "zitat": "23, 16 and 21 patients were randomized to placebo, "
                 "pioglitazone and metformin treatment groups respectively.",
    },
    ("yun2024:78", "intervention_group_size", "30"): {
        "kategorie": UNTERGRUPPE,
        "befund": "Die gewaehlte Tabelle druckt drei Raucherstrata (3/19/8); "
                  "die Gesamtgruppe 30 steht als Kopfangabe in T1.",
        "zitat": "Palmvitee,n = 30",
    },
    ("yun2024:79", "intervention_group_size", "30"): {
        "kategorie": UNTERGRUPPE,
        "befund": "Die gewaehlte Tabelle druckt drei Raucherstrata (3/19/8); "
                  "die Gesamtgruppe 30 steht als Kopfangabe in T1.",
        "zitat": "Palmvitee,n = 30",
    },
    # --- Gesamtpopulation versus analysierte Population --------------------
    ("yun2024:185", "comparator_group_size", "28"): {
        "kategorie": POPULATION,
        "befund": "Die Baseline-Tabelle druckt Placebo 33; die CTT-Auswertung "
                  "umfasst 28.",
        "zitat": "Fifty-seven subjects were assessed for CTT (placebo, n = 28; "
                 "RMD, n = 29).",
    },
    ("yun2024:194", "intervention_group_size", "169"): {
        "kategorie": POPULATION,
        "befund": "Tabelle 6 druckt 169/167, die gewaehlte Tabelle 145/140; "
                  "Fließtext: 328 eingeschlossen, 276 beendet.",
        "zitat": "Of 328 patients enrolled, 276 patients completed the trial "
                 "(140 in the treatment group and 136 in the placebo group).",
    },
    ("yun2024:194", "comparator_group_size", "167"): {
        "kategorie": POPULATION,
        "befund": "Tabelle 6 druckt 169/167, die gewaehlte Tabelle 145/140.",
        "zitat": "Of 328 patients enrolled, 276 patients completed the trial "
                 "(140 in the treatment group and 136 in the placebo group).",
    },
    ("yun2024:265", "intervention_group_size", "83"): {
        "kategorie": POPULATION,
        "befund": "242 randomisiert (83/80/79), 5 von der ITT-Analyse "
                  "ausgeschlossen; die gewaehlte Tabelle druckt 81/78/78.",
        "zitat": "Five patients were found ineligible during the batch assay at "
                 "the end of treatment (week 24) at the central laboratory, and "
                 "therefore were excluded from the intent-to-treat analysis.",
    },
    ("yun2024:265", "comparator_group_size", "79"): {
        "kategorie": POPULATION,
        "befund": "Placebo 79 randomisiert, 78 in der ITT-Tabelle.",
        "zitat": "242 patients were eligible and assigned randomly to placebo, "
                 "30 µg YIC and 60 µg YIC groups in a three-month period.",
    },
    ("yun2024:266", "intervention_group_size", "80"): {
        "kategorie": POPULATION,
        "befund": "60 µg YIC 80 randomisiert, 78 in der ITT-Tabelle.",
        "zitat": "242 patients were eligible and assigned randomly to placebo, "
                 "30 µg YIC and 60 µg YIC groups in a three-month period.",
    },
    ("yun2024:266", "comparator_group_size", "79"): {
        "kategorie": POPULATION,
        "befund": "Placebo 79 randomisiert, 78 in der ITT-Tabelle.",
        "zitat": "242 patients were eligible and assigned randomly to placebo, "
                 "30 µg YIC and 60 µg YIC groups in a three-month period.",
    },
    ("yun2024:531", "intervention_group_size", "289"): {
        "kategorie": POPULATION,
        "befund": "ITT 600 mg = 289, Safety-Population 307; die gewaehlte "
                  "Tabelle ist die Safety-Population.",
        "zitat": "A total of 776 (35.2%) patients with bipolar II depression "
                 "were included in the ITT population (283, 289, and 204 "
                 "patients received quetiapine 300 mg/day, quetiapine 600 "
                 "mg/day, or placebo, respectively).",
    },
    ("yun2024:531", "comparator_group_size", "204"): {
        "kategorie": POPULATION,
        "befund": "ITT Placebo = 204, Safety-Population 214.",
        "zitat": "A total of 776 (35.2%) patients with bipolar II depression "
                 "were included in the ITT population (283, 289, and 204 "
                 "patients received quetiapine 300 mg/day, quetiapine 600 "
                 "mg/day, or placebo, respectively).",
    },
    ("yun2024:532", "intervention_group_size", "283"): {
        "kategorie": POPULATION,
        "befund": "ITT 300 mg = 283, Safety-Population 298.",
        "zitat": "A total of 776 (35.2%) patients with bipolar II depression "
                 "were included in the ITT population (283, 289, and 204 "
                 "patients received quetiapine 300 mg/day, quetiapine 600 "
                 "mg/day, or placebo, respectively).",
    },
    ("yun2024:532", "comparator_group_size", "204"): {
        "kategorie": POPULATION,
        "befund": "ITT Placebo = 204, Safety-Population 214.",
        "zitat": "A total of 776 (35.2%) patients with bipolar II depression "
                 "were included in the ITT population (283, 289, and 204 "
                 "patients received quetiapine 300 mg/day, quetiapine 600 "
                 "mg/day, or placebo, respectively).",
    },
    ("yun2024:645", "intervention_group_size", "27"): {
        "kategorie": POPULATION,
        "befund": "Baseline 29/30, Ergebnis-Tabelle 27/26 (analysierte "
                  "Population).",
        "zitat": "Developmental outcomes from the Bayley Scales of Infant and "
                 "Toddler Development",
    },
    ("yun2024:645", "comparator_group_size", "26"): {
        "kategorie": POPULATION,
        "befund": "Baseline 29/30, Ergebnis-Tabelle 27/26.",
        "zitat": "Developmental outcomes from the Bayley Scales of Infant and "
                 "Toddler Development",
    },
    ("yun2024:647", "intervention_group_size", "27"): {
        "kategorie": POPULATION,
        "befund": "Baseline 29/30, Ergebnis-Tabelle 27/26.",
        "zitat": "Developmental outcomes from the Bayley Scales of Infant and "
                 "Toddler Development",
    },
    ("yun2024:647", "comparator_group_size", "26"): {
        "kategorie": POPULATION,
        "befund": "Baseline 29/30, Ergebnis-Tabelle 27/26.",
        "zitat": "Developmental outcomes from the Bayley Scales of Infant and "
                 "Toddler Development",
    },
    # --- Gesamtpopulation versus gedruckte Untergruppen --------------------
    ("yun2024:494", "intervention_group_size", "630"): {
        "kategorie": UNTERGRUPPE,
        "befund": "Die Tabelle druckt Ablehnungsgruende (4 (0.68) usw.); 630 "
                  "ist die Gesamtzahl der Proben (2/630 = 0.32).",
        "zitat": "The total number of blood samples included in the study "
                 "during July 2014 (post-training): 10 218 from CHC A, 4114 "
                 "from CHC B, 2279 from CDC C and 630 from CDC D.",
    },
    # --- Zeitpunkt ---------------------------------------------------------
    ("yun2024:445", "intervention_mean", "1.2"): {
        "kategorie": ZEITPUNKT,
        "befund": "Der Wert steht in derselben Tabelle in einer anderen "
                  "Zeitpunktspalte (r6/c3, r8/c2), nicht an der belegten.",
    },
    ("yun2024:445", "comparator_mean", "2.1"): {
        "kategorie": ZEITPUNKT,
        "befund": "Der Wert steht in derselben Tabelle in einer anderen "
                  "Zeitpunktspalte (r1/c1, r3/c2, r5/c1, r8/c1).",
    },
    ("yun2024:665", "intervention_mean", "103.4"): {
        "kategorie": ZEITPUNKT,
        "befund": "T1 druckt den Baselinewert 103.4 (±28.9); die gewaehlte "
                  "Tabelle druckt die Aenderung.",
    },
    ("yun2024:665", "intervention_standard_deviation", "28.9"): {
        "kategorie": ZEITPUNKT,
        "befund": "Baseline-Streuung aus T1 (103.4 (±28.9)).",
    },
    ("yun2024:665", "comparator_mean", "97.6"): {
        "kategorie": ZEITPUNKT,
        "befund": "T1 druckt den Baselinewert 97.6 (±20.8).",
    },
    ("yun2024:665", "comparator_standard_deviation", "20.8"): {
        "kategorie": ZEITPUNKT,
        "befund": "Baseline-Streuung aus T1 (97.6 (±20.8)).",
    },
    # --- Ungeklaert, aber belegt dokumentiert ------------------------------
    ("yun2024:335", "intervention_group_size", "45"): {
        "kategorie": UNERKLAERT,
        "befund": "Armvertauschung im Gold: der Text nennt dreimal Placebo 45 "
                  "und Aripiprazol 47; der Parser bindet wie der Text.",
        "zitat": "Ninety-two patients were randomized to placebo (n = 45) or "
                 "aripiprazole (n = 47).",
    },
    ("yun2024:336", "intervention_group_size", "45"): {
        "kategorie": UNERKLAERT,
        "befund": "Armvertauschung im Gold (Placebo 45, Aripiprazol 47).",
        "zitat": "Ninety-two patients were randomized to placebo (n = 45) or "
                 "aripiprazole (n = 47).",
    },
    ("yun2024:678", "intervention_group_size", "16"): {
        "kategorie": UNERKLAERT,
        "befund": "Bandgeometrie: (n=15) liegt ueber den Antibiotika-Spalten "
                  "6-10, das Probiotic-(n=16) ist auf c2/c5 zerlegt; der Text "
                  "nennt Antibiotika 16.",
        "zitat": "probiotic (n=16), antibiotic (n = 16) or placebo (n = 15)",
    },
    ("yun2024:682", "intervention_group_size", "16"): {
        "kategorie": UNERKLAERT,
        "befund": "Bandgeometrie wie yun2024:678 (verschobene Kopfzeile).",
        "zitat": "probiotic (n=16), antibiotic (n = 16) or placebo (n = 15)",
    },
    ("yun2024:421", "intervention_mean", "0.83"): {
        "kategorie": UNERKLAERT,
        "befund": "Wert nur im Fließtext (0.83 [SD, 0.22]); die Tabelle druckt "
                  "2.2 (1) / 2.7 (0.7).",
        "zitat": "0.83 [SD, 0.22]",
    },
    ("yun2024:421", "intervention_standard_deviation", "0.22"): {
        "kategorie": UNERKLAERT,
        "befund": "Streuung nur im Fließtext (0.83 [SD, 0.22]).",
        "zitat": "0.83 [SD, 0.22]",
    },
    ("yun2024:426", "comparator_group_size", "44"): {
        "kategorie": UNERKLAERT,
        "befund": "Die gewaehlte Tabelle druckt SNR-Werte; 44/49 stammen aus "
                  "einer anderen Tabelle (Short-Bore MR n = 44, Open MR n = 49).",
        "zitat": "examinations performed on the open MR scanner",
    },
    ("yun2024:196", "intervention_group_size", "24"): {
        "kategorie": UNERKLAERT,
        "befund": "Die gewaehlte Tabelle druckt Krebsereignisse mit 169/167; "
                  "24 erscheint im Dokument nur als Wochenzahl.",
    },
    ("yun2024:196", "comparator_group_size", "24"): {
        "kategorie": UNERKLAERT,
        "befund": "Wie intervention_group_size: keine Kopfangabe 24.",
    },
}

# Volltextbelege der beiden Armkonflikte (Phase 1, offline gelesen).
ARMKONFLIKTE = {
    "PMC5617873:T2": {
        "record_ids": ["yun2024:335", "yun2024:336"],
        "druck": ["Placebo (n = 45) Aripiprazole (n = 47)",
                  "Aripiprazole (n = 47)"],
        "belege": [
            ("Abstract", "Ninety-two patients were randomized to placebo "
                         "(n = 45) or aripiprazole (n = 47)."),
            ("Ergebnisse", "92 patients were randomly assigned to receive "
                           "placebo (n = 45) or aripiprazole (n = 47)."),
            ("Baseline-Tabelle", "Placebo (n = 45) Aripiprazole (n = 47) "
                                 "Total (n = 92)"),
            ("Gegenprobe", "Forty-two (93.3%) patients in the placebo group"),
            ("Gegenprobe", "the last dose of placebo corresponding to "
                           "aripiprazole (n = 45)"),
            ("Methoden", "Patients received flexibly dosed aripiprazole "
                         "(1--15 mg/day) or placebo."),
        ],
        "befund": "45 = Placebo (Vergleichsarm), 47 = Aripiprazol "
                  "(Interventionsarm); das Goldfeld fuehrt es umgekehrt.",
    },
    "PMC5777419:T2": {
        "record_ids": ["yun2024:678", "yun2024:682"],
        "druck": ["(n=16) (n=16) (n=15)"],
        "belege": [
            ("Methoden", "randomly assigned to a probiotic (n=16), antibiotic "
                         "(n = 16) or placebo (n = 15) group"),
            ("Analyse", "Forty-seven patients, 16 in the probiotic group, 16 "
                        "in the antibiotic group and 15 in the placebo group "
                        "were analyzed."),
            ("Baseline-Tabelle", "Probiotic group (n=16) Antibiotic group "
                                 "(n=16) Placebo group (n=15)"),
            ("Ergebnis-Tabelle", "Day 0 16 (100%) 16 (100%) 15 (100%)"),
        ],
        "befund": "Antibiotika = 16, Placebo = 15 (Gold richtig); die "
                  "Kopfbaender liegen verschoben ueber den Spalten.",
    },
}


def _gold(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list((record.get("gold") or {}).get("cells") or [])


def _norm(text: str) -> str:
    """Vergleichsform: Auszeichnung weg, Leerraum einfach."""
    text = re.sub(r"[*_]+", "", text or "")
    return re.sub(r"\s+", " ", text).strip().lower()


def _gedruckt(stelle: pv.Provenienz, wert: float) -> bool:
    """Wie in der Kursiv-Messung: Kopfangabe gleich, Zelle ueber den Text."""
    if stelle.quelle == pv.QUELLE_KOPF:
        return stelle.wert == wert
    return _zelltreffer(stelle.text, wert)


def _stellen(tables: Sequence[Any], context: Dict[str, Any]
             ) -> Dict[str, List[pv.Provenienz]]:
    """Je Feld alle Fundstellen der geladenen Tabellen, ohne Doppel."""
    out: Dict[str, List[pv.Provenienz]] = defaultdict(list)
    gesehen = set()
    for table in tables:
        for row_id, feld in reachable_cells(table, context):
            for stelle in pv.stellen(table, row_id, feld):
                # Je Feld entdoppeln: eine Verbundzelle ("1.3 (0.6)") traegt
                # Mittelwert und Streuung, das sind zwei Fundstellen.
                schluessel = (feld, stelle.tabelle, stelle.quelle,
                              stelle.zeile, tuple(stelle.spalten), stelle.text)
                if schluessel in gesehen:
                    continue
                gesehen.add(schluessel)
                out[feld].append(stelle)
    return dict(out)


def _dokument_tabellen(text: str, doc_id: str,
                       context: Dict[str, Any]) -> List[Any]:
    """Alle Tabellen des Dokuments, angereichert - nur fuer den Belegnachweis."""
    doc = parse_document(text, doc_id)
    for table in doc.tables:
        enrich_table(table, context)
    transfer_arms_within_document(doc.tables, context)
    transfer_arms_from_document(doc.tables, context, text)
    return doc.tables


def _wert_anderswo(alle: Sequence[Any], feld: str, wert: float,
                   ausschluss: Sequence[pv.Provenienz]) -> List[str]:
    """Orte ausserhalb der belegten Stellen, an denen ``wert`` gedruckt steht."""
    verboten = {(s.tabelle, s.zeile, tuple(s.spalten)) for s in ausschluss}
    orte = []
    for table in alle:
        for row in table.rows:
            for col_id in sorted(row.cells):
                if (table.table_id, row.row_id, (col_id,)) in verboten:
                    continue
                text = (row.cells[col_id].text or "")
                if _zelltreffer(text, wert):
                    orte.append(f"{table.table_id}:r{row.row_id}/c{col_id}")
        for band in table.header_bands:
            if _zelltreffer((band.text or ""), wert):
                orte.append(f"{table.table_id}:kopf c{band.col_start}-{band.col_end}")
        for fact in table.header_facts:
            if fact.get("value") == wert \
                    and field_for(ROLE_N, fact.get("arm") or None) == feld:
                orte.append(f"{table.table_id}:kopfangabe {fact.get('text')}")
    return sorted(set(orte))


def _klassifizieren(record_id: str, feld: str, raw: str, wert: float,
                    stellen: Sequence[pv.Provenienz], text: str,
                    alle: Sequence[Any]) -> Dict[str, Any]:
    """Eine Klasse je Feld - nur mit geprueftem Beleg, sonst unexplained."""
    beleg = BELEGE.get((record_id, feld, raw), {})
    kategorie = beleg.get("kategorie", UNERKLAERT)
    befund = beleg.get("befund", "Kein Beleg im Dokument gefunden.")
    zitat = beleg.get("zitat", "")
    zitat_geprueft = bool(zitat) and _norm(zitat) in _norm(text)
    kopfwerte = [s.wert for s in stellen
                 if s.quelle == pv.QUELLE_KOPF and s.wert is not None]
    anderswo = _wert_anderswo(alle, feld, wert, stellen)
    summe = sum(kopfwerte) if len(kopfwerte) > 1 else None
    geprueft = False
    if kategorie == SUMME:
        geprueft = summe is not None and abs(summe - wert) < 1e-9
    elif kategorie == POPULATION:
        geprueft = zitat_geprueft or bool(anderswo)
    elif kategorie == ZEITPUNKT:
        geprueft = bool(anderswo) or zitat_geprueft
    elif kategorie == UNTERGRUPPE:
        geprueft = zitat_geprueft or bool(anderswo)
    elif kategorie == UNERKLAERT:
        geprueft = True
    if not geprueft:
        befund += " [Beleg nicht verifiziert - als unexplained gefuehrt]"
        kategorie = UNERKLAERT
    return {
        "record_id": record_id,
        "table_id": next((s.tabelle for s in stellen), ""),
        "feld": feld,
        "raw": raw,
        "wert": wert,
        "kategorie": kategorie,
        "befund": befund,
        "zitat": zitat,
        "zitat_geprueft": zitat_geprueft,
        "kopfwerte": kopfwerte,
        "summe_kopfwerte": summe,
        "wert_sonst_gedruckt": anderswo[:6],
        "art": pv.feld_art(stellen),
        "sicherheit": pv.feld_sicherheit(stellen),
        "arm": pv.feld_arm(stellen),
        "stellen": [s.to_dict() for s in stellen],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    selection = json.loads(rb.DEFAULT_SELECTION.read_text(encoding="utf-8"))
    records = rb.load_records(rb.DEFAULT_RECORDS)
    grouped = rb.group_by_record(selection, None)

    felder: List[Dict[str, Any]] = []
    provenienz_je_feld: List[Dict[str, Any]] = []
    erreicht = wertgleich = 0
    je_art: Counter = Counter()
    je_sicherheit: Counter = Counter()
    je_arm: Counter = Counter()
    dokumente: Dict[str, Dict[str, Any]] = {}

    for record_id, entries in sorted(grouped.items()):
        record = records.get(record_id)
        if record is None:
            continue
        tables, text, _redundant = rb.load_tables(entries, record)
        if not tables:
            continue
        context = rb.context_of(record)
        stellen = _stellen(tables, context)
        doc_id = str(record["document"]["id"])
        if doc_id not in dokumente:
            dokumente[doc_id] = {"text": text, "tabellen": None}
        if dokumente[doc_id]["tabellen"] is None:
            dokumente[doc_id]["tabellen"] = _dokument_tabellen(text, doc_id, context)
        alle = dokumente[doc_id]["tabellen"]

        for gold_cell in _gold(record):
            feld = gold_cell["field"]
            if feld not in stellen:
                continue
            orte = stellen[feld]
            erreicht += 1
            gleich = any(_gedruckt(s, gold_cell["value"]) for s in orte)
            wertgleich += 1 if gleich else 0
            je_art[pv.feld_art(orte)] += 1
            je_sicherheit[pv.feld_sicherheit(orte)] += 1
            je_arm[pv.feld_arm(orte)] += 1
            provenienz_je_feld.append({
                "record_id": record_id,
                "feld": feld,
                "raw": gold_cell.get("raw"),
                "wertgleich": gleich,
                "art": pv.feld_art(orte),
                "sicherheit": pv.feld_sicherheit(orte),
                "arm": pv.feld_arm(orte),
                "stellen": [s.to_dict() for s in orte],
            })
            if gleich:
                continue
            felder.append(_klassifizieren(
                record_id, feld, str(gold_cell.get("raw")), gold_cell["value"],
                orte, text, alle))

    klassen = Counter(f["kategorie"] for f in felder)
    bericht = {
        "bilanz": {
            "strukturell_erreichbar": erreicht,
            "wertgleich": wertgleich,
            "nicht_wertgleich": erreicht - wertgleich,
        },
        "fehlerklassen": dict(sorted(klassen.items())),
        "provenienz": {
            "je_art": dict(sorted(je_art.items())),
            "je_sicherheit": dict(sorted(je_sicherheit.items())),
            "je_arm": dict(sorted(je_arm.items())),
            "felder": provenienz_je_feld,
        },
        "nicht_wertgleich": sorted(
            felder, key=lambda f: (f["record_id"], f["feld"])),
        "armkonflikte": ARMKONFLIKTE,
    }
    Path(args.out).write_text(
        json.dumps(bericht, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    print(f"erreichbar {erreicht}, wertgleich {wertgleich}, "
          f"nicht wertgleich {erreicht - wertgleich}")
    print("Klassen:", bericht["fehlerklassen"])
    print("Art:", bericht["provenienz"]["je_art"],
          "Sicherheit:", bericht["provenienz"]["je_sicherheit"],
          "Arm:", bericht["provenienz"]["je_arm"])
    for feld in bericht["nicht_wertgleich"]:
        print(f"  {feld['kategorie']:20} {feld['record_id']:12} "
              f"{feld['feld']:32} {feld['raw']:>7} "
              f"art={feld['art']:10} arm={feld['arm']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
