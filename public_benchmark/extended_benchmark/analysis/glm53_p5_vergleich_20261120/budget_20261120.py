#!/usr/bin/env python
"""Die 33 Budgetabbrueche des P5-Laufs, Schwerpunkt auf den 13 ohne Strukturhypothese.

Rein lesend auf `iterativ/ergebnisse/sprint48_budgetdiagnose.json`. Kein
Netzaufruf, keine Prediction geschrieben, kein Gold beruehrt.

Zusaetzlich zu den dortigen Merkmalen werden drei Kennzahlen gerechnet, die die
Hypothesen pruefbar machen:

- `prompt_aufschlag` = prompt_zeichen - text_zeichen (was die Pipeline dem
  Quelltext hinzufuegt),
- `reasoning_je_text` = reasoning_zeichen / text_zeichen (wie viel Reasoning je
  Zeichen Quelle verbraucht wird),
- `reasoning_je_goldzelle` = reasoning_zeichen / Goldzellen (Aufwand je Trefferflaeche).

Aufruf:
    .venv/bin/python analysis/glm53_p5_vergleich_20261120/budget_20261120.py
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent.parent
QUELLE = BENCH / "iterativ" / "ergebnisse" / "sprint48_budgetdiagnose.json"


def median(werte: list[float]) -> float | None:
    return round(statistics.median(werte), 2) if werte else None


def q(werte: list[float], anteil: float) -> float | None:
    if not werte:
        return None
    sortiert = sorted(werte)
    pos = min(len(sortiert) - 1, int(round(anteil * (len(sortiert) - 1))))
    return round(sortiert[pos], 2)


def kennzahlen(faelle: list[dict[str, Any]]) -> dict[str, Any]:
    reasoning = [f["lauf"]["reasoning_zeichen"] for f in faelle]
    prompt = [f["struktur"]["prompt_zeichen"] for f in faelle]
    text = [f["struktur"]["text_zeichen"] for f in faelle]
    aufschlag = [p - t for p, t in zip(prompt, text)]
    je_text = [r / t for r, t in zip(reasoning, text) if t]
    gold = [f["gold"]["zellen"] for f in faelle]
    je_gold = [r / g for r, g in zip(reasoning, gold) if g]
    dauer = [f["lauf"]["dauer_s"] for f in faelle]
    return {
        "n": len(faelle),
        "reasoning_median": median(reasoning),
        "reasoning_q25": q(reasoning, 0.25),
        "reasoning_q75": q(reasoning, 0.75),
        "prompt_median": median(prompt),
        "text_median": median(text),
        "aufschlag_median": median(aufschlag),
        "reasoning_je_text_median": median(je_text),
        "gold_median": median(gold),
        "reasoning_je_goldzelle_median": median(je_gold),
        "dauer_median": median(dauer),
        "tabellen_median": median([f["struktur"]["tabellen"] for f in faelle]),
        "datenzellen_median": median([f["struktur"]["datenzellen_summe"] for f in faelle]),
        "ohne_tabelle": sum(1 for f in faelle if f["struktur"]["tabellen"] == 0),
        "ohne_zielfeld": sum(1 for f in faelle if f["struktur"]["tabellen_mit_zielfeld"] == 0),
        "gruppenkopf": sum(1 for f in faelle if f["struktur"]["gruppenkopf_zellen"] > 0),
        "binary": sum(1 for f in faelle if f["kontext"]["outcome_typ"] == "binary"),
        "continuous": sum(1 for f in faelle if f["kontext"]["outcome_typ"] == "continuous"),
    }


def main() -> int:
    daten = json.loads(QUELLE.read_text(encoding="utf-8"))
    faelle = daten["faelle"]
    abbruch = [f for f in faelle if f["gruppe"] == "budget_abbruch"]
    erfolg = [f for f in faelle if f["gruppe"] == "erfolg"]

    def hat_struktur_hypothese(f: dict[str, Any]) -> bool:
        """H1, H2, H3weit oder H6 trifft zu (H3weit ist das ODER aus H3/H3G/H3S)."""
        h = f.get("hypothesen") or {}
        return any(bool(h.get(name)) for name in ("H1", "H2", "H3weit", "H6"))

    ohne = [f for f in abbruch if not hat_struktur_hypothese(f)]
    mit = [f for f in abbruch if hat_struktur_hypothese(f)]

    print(f"Faelle gesamt {len(faelle)} | Abbruch {len(abbruch)} | Erfolg {len(erfolg)}")
    print(f"Ohne Strukturhypothese {len(ohne)} | mit {len(mit)}")
    print("IDs ohne Strukturhypothese:", ",".join(f["record_id"] for f in ohne))
    print("\nHaeufigkeit je Hypothese:", {
        name: sum(1 for f in abbruch if (f.get("hypothesen") or {}).get(name)) for name in
        ("H1", "H2", "H3", "H3G", "H3S", "H3weit", "H4", "H4a", "H4b", "H5", "H6", "H7")
    })

    gruppen = {"abbruch_ohne": ohne, "abbruch_mit": mit, "erfolg": erfolg}
    ergebnis: dict[str, Any] = {"kennzahlen": {}, "faelle": {}}
    for name, menge in gruppen.items():
        ergebnis["kennzahlen"][name] = kennzahlen(menge)

    print("\n| Kennzahl | ohne Struktur (13) | mit Struktur (20) | Erfolge (67) |")
    print("|---|---:|---:|---:|")
    k = ergebnis["kennzahlen"]
    labels = [
        ("reasoning_median", "Reasoning-Zeichen Median"),
        ("reasoning_q25", "Reasoning-Zeichen Q25"),
        ("reasoning_q75", "Reasoning-Zeichen Q75"),
        ("prompt_median", "Prompt-Zeichen Median"),
        ("text_median", "Text-Zeichen Median"),
        ("aufschlag_median", "Prompt-Aufschlag Median"),
        ("reasoning_je_text_median", "Reasoning je Textzeichen"),
        ("gold_median", "Goldzellen Median"),
        ("dauer_median", "Dauer s Median"),
        ("tabellen_median", "Tabellen Median"),
        ("datenzellen_median", "Datenzellen Median"),
        ("ohne_tabelle", "ohne parsebare Tabelle"),
        ("ohne_zielfeld", "ohne Tabelle mit Zielfeld"),
        ("gruppenkopf", "mit Gruppenkopf"),
        ("binary", "binaeres Outcome"),
        ("continuous", "kontinuierliches Outcome"),
    ]
    for feld, label in labels:
        print(f"| {label} | {k['abbruch_ohne'][feld]} | {k['abbruch_mit'][feld]} | {k['erfolg'][feld]} |")

    for f in ohne + mit:
        lauf = f["lauf"]
        st = f["struktur"]
        eintrag = {
            "gruppe": "ohne_struktur" if f in ohne else "mit_struktur",
            "dokument": f["publikation"]["dokument_id"],
            "outcome_typ": f["kontext"]["outcome_typ"],
            "goldzellen": f["gold"]["zellen"],
            "reasoning": lauf["reasoning_zeichen"],
            "prompt": st["prompt_zeichen"],
            "text": st["text_zeichen"],
            "aufschlag": st["prompt_zeichen"] - st["text_zeichen"],
            "reasoning_je_text": round(lauf["reasoning_zeichen"] / st["text_zeichen"], 2) if st["text_zeichen"] else None,
            "tabellen": st["tabellen"],
            "captions": st["md_captions"],
            "pipe_zeilen": st["md_pipe_zeilen"],
            "datenzellen": st["datenzellen_summe"],
            "kopfebenen": st["kopfebenen_max"],
            "gruppenkopf": st["gruppenkopf_zellen"],
            "dauer": lauf["dauer_s"],
            "hypothesen": [n for n, wert in (f.get("hypothesen") or {}).items() if wert],
            "vorlaeufe": [(v["lauf"], v["budget"], v["klasse"]) for v in f.get("fruehere_laeufe") or []],
        }
        ergebnis["faelle"][f["record_id"]] = eintrag

    print("\nFaelle ohne Strukturhypothese:")
    print("| Record | Dokument | Typ | Gold | Reasoning | Prompt | Aufschlag | R/Text | Tab. | Pipe | Dauer |")
    print("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for f in ohne:
        e = ergebnis["faelle"][f["record_id"]]
        print(f"| `{f['record_id']}` | {e['dokument']} | {e['outcome_typ']} | {e['goldzellen']} | "
              f"{e['reasoning']} | {e['prompt']} | {e['aufschlag']} | {e['reasoning_je_text']} | "
              f"{e['tabellen']} | {e['pipe_zeilen']} | {e['dauer']} |")

    # Vorlauf-Historie: wie oft war derselbe Record schon bei 8000 ein Abbruch?
    print("\nVorlauf-Historie der 13:")
    for f in ohne:
        e = ergebnis["faelle"][f["record_id"]]
        print(f"  {f['record_id']}: {e['vorlaeufe']}")

    (HIER / "budget_20261120.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\ngeschrieben:", HIER / "budget_20261120.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
