#!/usr/bin/env python
"""Kategorisiert die fehlenden Goldzellen des GLM-Laufs auf Yun-699.

Ausgangspunkt sind alle Goldzellen, fuer die die GLM-Zeile keinen Wert liefert
(im Lauf `yun699_8000_alle_20261117` sind das 652). Jede Zelle wird genau einer
Kategorie zugeordnet. Die Zuordnung ist **lexikalisch und automatisch**: gesucht
wird die Goldzahl im gelieferten Auszug und, wenn sie dort fehlt, im
Volltext-XML. Das ist keine menschliche Annotation und ersetzt keine; es macht
aber sichtbar, wo die Information liegt und wo sie fehlt.

Kategorien (in dieser Prioritaetsreihenfolge):

1. `technischer_ausfall`   – Record endete mit Fehlerklasse (z. B. length).
2. `leere_antwort`         – Record lieferte eine Antwort ohne Zellen.
3. `prozent_statt_anzahl`  – Event-Zahl fehlt, im Text steht nur der Prozentwert.
4. `arm_konflikt`          – Zahl steht nur beim anderen Arm.
5. `zeitpunkt`             – Zahl steht mehrfach mit verschiedenen Zeitangaben.
6. `tabelle`               – Zahl steht in einem Tabellenblock.
7. `fliess_text`           – Zahl steht im Fliesstext.
8. `abbildung`             – Zahl steht in einer Abbildungsunterschrift.
9. `nur_volltext`          – Zahl fehlt im Auszug, steht aber im Volltext-XML.
10. `nicht_auffindbar`     – Zahl steht in keiner der beiden Quellen.

Aufruf:
    python public_benchmark/extended_benchmark/iterativ/fehleranalyse_zellen.py \
        --out public_benchmark/extended_benchmark/iterativ/ergebnisse/fehleranalyse_glm699.json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import gemeinsam as g

ZEIT_MUSTER = re.compile(
    r"(?i)\b(baseline|week|weeks|month|months|day|days|year|years|follow[- ]?up|"
    r"at \d+ ?(?:weeks?|months?|days?|years?))\b"
)


def kategorie_fuer_zelle(
    record: dict,
    feld: str,
    zeile: dict,
    doc: str,
    doc_bloecke: list[dict],
    xml: str,
) -> dict:
    """Liefert `{kategorie, begruendung, fundstelle}` fuer eine fehlende Zelle."""
    roh = g.gold_roh(record).get(feld, "")
    arm = "intervention" if feld.startswith("intervention") else "comparator"
    eigen = g.arm_begriffe(record, arm)
    fremd = g.arm_begriffe(record, "comparator" if arm == "intervention" else "intervention")

    fehlerklasse = str(zeile.get("fehlerklasse") or "")
    if fehlerklasse:
        return {
            "kategorie": "technischer_ausfall",
            "begruendung": fehlerklasse,
            "fundstelle": "",
        }
    if not (zeile.get("rows") or []):
        return {
            "kategorie": "leere_antwort",
            "begruendung": "Antwort ohne Zellen",
            "fundstelle": "",
        }

    positionen = g.finde_zahl(doc, roh)
    if positionen:
        typen = Counter(g.block_typ_an(doc_bloecke, p) for p in positionen)
        bei_eigen = any(g.naehe(doc, p, eigen, 260) for p in positionen)
        bei_fremd = any(g.naehe(doc, p, fremd, 260) for p in positionen) if fremd else False
        # Zeitangaben in der Naehe: mehrere verschiedene Labels gelten als mehrdeutig.
        labels = set()
        for p in positionen:
            umfeld = doc[max(0, p - 300) : p + 300]
            for treffer in ZEIT_MUSTER.finditer(umfeld):
                labels.add(treffer.group(1).lower())
        if bei_fremd and not bei_eigen:
            return {
                "kategorie": "arm_konflikt",
                "begruendung": "Zahl steht nur im Umfeld des anderen Arms",
                "fundstelle": doc[max(0, positionen[0] - 120) : positionen[0] + 120],
            }
        if len(labels) >= 2:
            return {
                "kategorie": "zeitpunkt",
                "begruendung": "Zahl steht bei mehreren Zeitangaben: " + ", ".join(sorted(labels)[:3]),
                "fundstelle": doc[max(0, positionen[0] - 120) : positionen[0] + 120],
            }
        if typen.most_common(1)[0][0] == "tabelle":
            return {
                "kategorie": "tabelle",
                "begruendung": "Zahl in Tabellenblock",
                "fundstelle": doc[max(0, positionen[0] - 120) : positionen[0] + 120],
            }
        if typen.most_common(1)[0][0] == "abbildung":
            return {
                "kategorie": "abbildung",
                "begruendung": "Zahl in Abbildungsunterschrift",
                "fundstelle": doc[max(0, positionen[0] - 120) : positionen[0] + 120],
            }
        return {
            "kategorie": "fliess_text",
            "begruendung": "Zahl im Fliesstext",
            "fundstelle": doc[max(0, positionen[0] - 120) : positionen[0] + 120],
        }

    # Zahl fehlt im Auszug: steht sie als Prozentwert da?
    if feld.endswith("_events"):
        n = g.gold_werte(record).get(f"{arm}_group_size")
        ereignisse = g.als_zahl(roh)
        if n and ereignisse is not None:
            kandidaten = {
                f"{round(ereignisse / n * 100):d}%",
                f"{ereignisse / n * 100:.1f}%",
            }
            for kandidat in kandidaten:
                if kandidat in doc:
                    return {
                        "kategorie": "prozent_statt_anzahl",
                        "begruendung": f"nur Prozentwert {kandidat} gefunden",
                        "fundstelle": kandidat,
                    }

    if xml and g.finde_zahl(xml, roh):
        return {
            "kategorie": "nur_volltext",
            "begruendung": "Zahl fehlt im gelieferten Auszug, steht im Volltext",
            "fundstelle": "",
        }
    return {"kategorie": "nicht_auffindbar", "begruendung": "in Auszug und Volltext nicht gefunden", "fundstelle": ""}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--modell", default="glm")
    parser.add_argument("--max-beispiele", type=int, default=4)
    args = parser.parse_args()

    records = g.lade_records()
    zeilen = g.lade_modell(g.lies(g.VORLAUF), args.modell)

    docs: dict[str, str] = {}
    bloecke_cache: dict[str, list[dict]] = {}
    xml_cache: dict[str, str] = {}

    eintraege: list[dict] = []
    for record_id, record in records.items():
        zeile = zeilen.get(record_id, {})
        gold = g.gold_werte(record)
        modell = g.modell_werte(zeile) if zeile else {}
        for feld, wert in gold.items():
            if feld in modell:
                continue
            pfad = record["document"]["path"]
            if pfad not in docs:
                docs[pfad] = g.dokument(record)
                bloecke_cache[pfad] = g.bloecke(docs[pfad])
            if record_id not in xml_cache:
                xml_cache[record_id] = g.volltext(record)
            befund = kategorie_fuer_zelle(
                record,
                feld,
                zeile,
                docs[pfad],
                bloecke_cache[pfad],
                xml_cache[record_id],
            )
            eintraege.append(
                {
                    "record_id": record_id,
                    "feld": feld,
                    "arm": "intervention" if feld.startswith("intervention") else "comparator",
                    "gold": wert,
                    "gold_roh": g.gold_roh(record).get(feld, ""),
                    "outcome_type": record["context"].get("outcome_type"),
                    "kategorie": befund["kategorie"],
                    "begruendung": befund["begruendung"],
                    "fundstelle": befund["fundstelle"].strip()[:400],
                }
            )

    nach_kat = Counter(e["kategorie"] for e in eintraege)
    nach_feld = defaultdict(Counter)
    for e in eintraege:
        nach_feld[e["feld"]][e["kategorie"]] += 1
    beispiele: dict[str, list[dict]] = defaultdict(list)
    for e in eintraege:
        if len(beispiele[e["kategorie"]]) < args.max_beispiele:
            beispiele[e["kategorie"]].append(
                {"record_id": e["record_id"], "feld": e["feld"], "gold": e["gold"], "begruendung": e["begruendung"]}
            )

    gesamt = len(eintraege)
    ergebnis = {
        "modell": args.modell,
        "lauf": "yun699_8000_alle_20261117",
        "fehlende_zellen": gesamt,
        "kategorien": dict(nach_kat.most_common()),
        "anteile": {k: round(v / gesamt, 4) for k, v in nach_kat.most_common()},
        "je_feld": {feld: dict(z) for feld, z in nach_feld.items()},
        "beispiele": beispiele,
        "zellen": eintraege,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{gesamt} fehlende Zellen, Kategorien:")
    for kategorie, anzahl in nach_kat.most_common():
        print(f"  {kategorie:22} {anzahl:5}  {anzahl / gesamt:6.1%}")
    print(f"geschrieben: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
