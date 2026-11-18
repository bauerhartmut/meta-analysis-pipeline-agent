"""Positivkontrolle fuer die P5-Auswertung.

Erfundene, aber feste Prediction-Datei mit bekannten Ergebnissen: Rettungen mit
richtigen und falschen Werten, eine leere Antwort, ein weiter ausgefallener
Record, ein im neuen Lauf fehlender Record, ein Record ohne Goldzellen und eine
Vorhersage, die denselben Feld/Arm-Schluessel ueber zwei Zeitpunkte streut.

Der Lauf prueft, ob `werte_p5_aus.auswerten()` genau die vorher ausgerechneten
Summen liefert, und schreibt Ist und Soll nebeneinander. Weicht etwas ab, endet
das Skript mit Exit 1 — die Kontrolle kann also nicht stillschweigend kippen.

Aufruf:
    python yun_full/positivkontrolle_p5.py

Ergebnis:
    iterativ/kontrolle/p5_positivkontrolle/{alt,neu}.jsonl
    iterativ/ergebnisse/p5_positivkontrolle_20261118.{json,md}
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent

try:  # als Skript aus extended_benchmark/ gestartet
    from extended_benchmark.yun_full import werte_p5_aus as p5
except ModuleNotFoundError:
    sys.path.insert(0, str(BENCH.parent))
    from extended_benchmark.yun_full import werte_p5_aus as p5

KONTROLLE = BENCH / "iterativ" / "kontrolle" / "p5_positivkontrolle"
ARTEFAKT = BENCH / "iterativ" / "ergebnisse" / "p5_positivkontrolle_20261118"

# Alle ids der Kontrolle. Die Klassen sind absichtlich gemischt, damit die
# Aufteilung nach ursprunglicher Fehlerklasse wirklich zwei Zeilen hat.
IDS = ["k1", "k2", "k3", "k4", "k5", "k6", "k7", "k8"]

GOLD: dict[str, list[tuple[str, str, float]]] = {
    "k1": [
        ("intervention_mean", "intervention", 0.77),
        ("comparator_mean", "comparator", 0.04),
        ("intervention_group_size", "intervention", 251.0),
    ],
    "k2": [("intervention_mean", "intervention", 1.20), ("comparator_mean", "comparator", 0.50)],
    "k3": [("intervention_mean", "intervention", 0.77)],
    "k4": [("intervention_events", "intervention", 12.0), ("comparator_events", "comparator", 9.0)],
    "k5": [("intervention_mean", "intervention", 0.30)],
    "k6": [("comparator_mean", "comparator", 0.11)],
    "k7": [("intervention_standard_deviation", "intervention", 0.50)],
    "k8": [],
}

# Alt = die Ausfallzeilen der Lesekopie. k6 fehlt im neuen Lauf, alle anderen
# sind angelegt; k7 stammt aus einer anderen Fehlerklasse.
KLASSE_ALT = {rid: "length_ohne_ergebnis" for rid in IDS}
KLASSE_ALT["k7"] = "json_kaputt"

VORHERSAGE: dict[str, dict[str, Any]] = {
    # drei richtige Zellen, je Schluessel ein Zeitpunkt
    "k1": {"fehler": "", "zellen": [
        {"field": "intervention_mean", "arm": "intervention", "value": 0.77, "timepoint": "30 days"},
        {"field": "comparator_mean", "arm": "comparator", "value": 0.04, "timepoint": "30 days"},
        {"field": "intervention_group_size", "arm": "intervention", "value": 251,
         "timepoint": "30 days"},
    ]},
    # Schluessel getroffen, Werte falsch
    "k2": {"fehler": "", "zellen": [
        {"field": "intervention_mean", "arm": "intervention", "value": 1.30, "timepoint": "30 days"},
        {"field": "comparator_mean", "arm": "comparator", "value": 0.60, "timepoint": "30 days"},
    ]},
    # derselbe Feld/Arm-Schluessel ueber zwei Zeitpunkte: grosszuegig ein Treffer,
    # streng keiner
    "k3": {"fehler": "", "zellen": [
        {"field": "intervention_mean", "arm": "intervention", "value": 0.77, "timepoint": "30 days"},
        {"field": "intervention_mean", "arm": "intervention", "value": 0.80, "timepoint": "60 days"},
    ]},
    # leere Antwort
    "k4": {"fehler": "", "zellen": []},
    # weiterhin ausgefallen
    "k5": {"fehler": "length_ohne_ergebnis", "zellen": []},
    # k6 fehlt ganz
    # andere Ursprungsklasse, richtige Zelle
    "k7": {"fehler": "", "zellen": [
        {"field": "intervention_standard_deviation", "arm": "intervention", "value": 0.5,
         "timepoint": "12 weeks"},
    ]},
    # keine Goldzellen: technisch und auswertbar, aber nicht in der Golddeckung
    "k8": {"fehler": "", "zellen": [
        {"field": "intervention_group_size", "arm": "intervention", "value": 100,
         "timepoint": "30 days"},
    ]},
}

# Vorher von Hand ausgerechnet, nicht vom Skript erzeugt.
ERWARTET: dict[str, Any] = {
    "grundgesamtheit": 8,
    "ids_ohne_altzeile": [],
    "status": {"gerettet": 5, "fertig_ohne_zellen": 1, "weiter_ausfall": 1, "fehlt": 1},
    "stufen": {
        "ids": 8,
        "technisch": 6,
        "auswertbar": 5,
        "inhaltlich": 3,
        "inhaltlich_zeitpunkt": 2,
    },
    "zellen_neu": 9,
    "zellen_neu_mit_zeitpunkt": 9,
    "goldzellen_bewertbar": 11,
    "goldzellen_mit_zeitpunkt": 0,
    "adressiert": 7,
    "adressiert_zeitpunkt": 6,
    "wertgleich": 5,
    "wertgleich_zeitpunkt": 4,
    "zeitpunkt_mehrdeutig": 1,
    "nach_klasse": {
        "length_ohne_ergebnis": {
            "ids": 7,
            "technisch": 5,
            "auswertbar": 4,
            "leer": 1,
            "weiter_ausfall": 1,
            "fehlt": 1,
            "goldzellen": 10,
            "adressiert": 6,
            "adressiert_zeitpunkt": 5,
            "wertgleich": 4,
            "wertgleich_zeitpunkt": 3,
        },
        "json_kaputt": {
            "ids": 1,
            "technisch": 1,
            "auswertbar": 1,
            "leer": 0,
            "weiter_ausfall": 0,
            "fehlt": 0,
            "goldzellen": 1,
            "adressiert": 1,
            "adressiert_zeitpunkt": 1,
            "wertgleich": 1,
            "wertgleich_zeitpunkt": 1,
        },
    },
}


def _alt_zeile(rid: str) -> dict[str, Any]:
    return {
        "record_id": rid,
        "model": "glm",
        "fehlerklasse": KLASSE_ALT[rid],
        "failed": True,
        "completion_tokens": 24000,
        "predicted": {"cells": []},
    }


def _neu_zeile(rid: str) -> dict[str, Any]:
    daten = VORHERSAGE[rid]
    return {
        "record_id": rid,
        "model": "glm",
        "fehlerklasse": daten["fehler"],
        "failed": bool(daten["fehler"]),
        "completion_tokens": 1200,
        "reasoning_chars": 4000,
        "predicted": {"cells": daten["zellen"]},
    }


def _records() -> dict[str, dict[str, Any]]:
    return {
        rid: {
            "record_id": rid,
            "gold": {"cells": [{"field": f, "arm": a, "value": v} for f, a, v in GOLD[rid]]},
        }
        for rid in IDS
    }


def schreibe_fixture() -> tuple[Path, Path]:
    """Schreibt alt/neu als JSONL, damit die Kontrolle wiederholbar ist."""
    KONTROLLE.mkdir(parents=True, exist_ok=True)
    alt = KONTROLLE / "alt.jsonl"
    neu = KONTROLLE / "neu.jsonl"
    alt.write_text(
        "".join(json.dumps(_alt_zeile(rid), ensure_ascii=False) + "\n" for rid in IDS),
        encoding="utf-8",
    )
    neu.write_text(
        "".join(
            json.dumps(_neu_zeile(rid), ensure_ascii=False) + "\n"
            for rid in IDS
            if rid in VORHERSAGE
        ),
        encoding="utf-8",
    )
    return alt, neu


def werte() -> dict[str, Any]:
    """Rechnet die Kontrolle im Speicher, ohne Dateien anzulegen."""
    return p5.auswerten(
        [_alt_zeile(rid) for rid in IDS],
        [_neu_zeile(rid) for rid in IDS if rid in VORHERSAGE],
        _records(),
        modell="glm",
        ids=list(IDS),
    )


def pruefe(werte: dict[str, Any]) -> list[str]:
    """Vergleicht Ist gegen Soll; gibt die Abweichungen als Text zurueck."""
    abweichungen: list[str] = []
    for feld, soll in ERWARTET.items():
        ist = werte.get(feld)
        if feld == "nach_klasse":
            for klasse, klassen_soll in soll.items():
                klassen_ist = (ist or {}).get(klasse)
                if klassen_ist is None:
                    abweichungen.append(f"nach_klasse[{klasse}]: fehlt")
                    continue
                for name, wert in klassen_soll.items():
                    if klassen_ist.get(name) != wert:
                        abweichungen.append(
                            f"nach_klasse[{klasse}].{name}: ist {klassen_ist.get(name)}, soll {wert}"
                        )
            continue
        if ist != soll:
            abweichungen.append(f"{feld}: ist {ist}, soll {soll}")
    return abweichungen


def _rel(pfad: Path) -> str:
    try:
        return str(pfad.relative_to(BENCH.parent))
    except ValueError:
        return str(pfad)


def bericht(werte: dict[str, Any], abweichungen: list[str], alt: Path, neu: Path) -> str:
    zeilen = [
        "# Positivkontrolle der P5-Auswertung",
        "",
        "Erfundene Prediction-Datei mit vorher ausgerechneten Sollwerten. Die Zahlen "
        "unten sind von Hand bestimmt, nicht aus dem Skript abgeleitet; das Skript "
        "vergleicht nur.",
        "",
        f"Fixture: `{_rel(alt)}` und `{_rel(neu)}`.",
        "",
        "## Soll und Ist",
        "",
        "| Groesse | Soll | Ist |",
        "|---|---:|---:|",
    ]
    for feld, soll in ERWARTET.items():
        if feld == "nach_klasse":
            continue
        ist = werte.get(feld)
        zeilen.append(f"| `{feld}` | {soll} | {ist} |")

    for klasse, klassen_soll in ERWARTET["nach_klasse"].items():
        zeilen += ["", f"### Klasse `{klasse}`", "", "| Groesse | Soll | Ist |", "|---|---:|---:|"]
        klassen_ist = (werte.get("nach_klasse") or {}).get(klasse) or {}
        for name, wert in klassen_soll.items():
            zeilen.append(f"| `{name}` | {wert} | {klassen_ist.get(name)} |")

    zeilen += [
        "",
        "## Ergebnis",
        "",
        (
            f"**Alle {sum(1 for f in ERWARTET if f != 'nach_klasse')} Kennzahlen und "
            f"{sum(len(v) for v in ERWARTET['nach_klasse'].values())} Klassenzahlen stimmen.**"
            if not abweichungen
            else "**Abweichungen:**"
        ),
    ]
    if abweichungen:
        zeilen += [""] + [f"- {text}" for text in abweichungen]

    zeilen += [
        "",
        "Was die Kontrolle abdeckt: richtige Zellen, Schluessel ohne richtigen Wert, "
        "eine leere Antwort, ein weiter ausgefallener Record, ein fehlender Record, "
        "ein Record ohne Goldzellen und eine Vorhersage mit zwei Zeitpunkten auf "
        "demselben Feld/Arm-Schluessel. Genau dort muss die grosszuegige Zaehlung "
        "einen Treffer melden und die strenge keinen.",
        "",
    ]
    return "\n".join(zeilen) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(ARTEFAKT.with_suffix(".json")))
    parser.add_argument("--md", default=str(ARTEFAKT.with_suffix(".md")))
    args = parser.parse_args()

    alt, neu = schreibe_fixture()
    werte = p5.auswerten(
        p5.lade(alt), p5.lade(neu), _records(), modell="glm", ids=list(IDS)
    )
    abweichungen = pruefe(werte)
    text = bericht(werte, abweichungen, alt, neu)

    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(
        json.dumps(
            {"soll": ERWARTET, "ist": {k: v for k, v in werte.items() if k not in {"bewertbar", "nicht_bewertbar"}}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    Path(args.md).write_text(text, encoding="utf-8")
    print(text)
    return 0 if not abweichungen else 1


if __name__ == "__main__":
    raise SystemExit(main())
