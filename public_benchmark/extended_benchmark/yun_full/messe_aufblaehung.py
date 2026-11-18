"""Misst offline, wie weit die grosszuegige Feld/Arm-Zaehlung uebersteigt.

Grundlage sind ausschliesslich die 559 erfolgreichen `glm`-Zeilen mit Zellen aus
der Lesekopie. Fuer jede Zeile werden Goldzellen, adressierte Goldzellen (Feld und
Arm) und adressierte Goldzellen mit eindeutigem Zeitpunkt gezaehlt; die Differenz
ist die Aufblaehung, die eine Rettung ohne Zeitpunktpruefung zu gut aussehen
laesst. Kein Netzlauf.

Aufruf:
    python yun_full/messe_aufblaehung.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:  # als Skript aus extended_benchmark/ gestartet
    from extended_benchmark.yun_full.werte_p5_aus import (
        BENCH,
        deckung,
        deckung_mit_zeitpunkt,
        lade,
        mehrdeutig,
        schluessel,
        zeitpunkt,
        zellen,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from extended_benchmark.yun_full.werte_p5_aus import (
        BENCH,
        deckung,
        deckung_mit_zeitpunkt,
        lade,
        mehrdeutig,
        schluessel,
        zeitpunkt,
        zellen,
    )

LESEKOPIE = BENCH / "runs" / "_lesekopie_20261118" / "predictions.jsonl"
RECORDS = BENCH / "yun_full" / "records" / "yun699.jsonl"
MODELL = "glm"


def messe(zeilen: list[dict[str, Any]], records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    erfolgreich = [
        z
        for z in zeilen
        if z.get("model") == MODELL
        and str(z.get("fehlerklasse") or "").strip().lower() in {"", "ok"}
        and zellen(z)
    ]
    eintraege: list[dict[str, Any]] = []
    for zeile in erfolgreich:
        rid = zeile["record_id"]
        gold = list(((records.get(rid) or {}).get("gold") or {}).get("cells") or [])
        vorhergesagt = zellen(zeile)
        adressiert, wertgleich = deckung(gold, vorhergesagt)
        adressiert_streng, wertgleich_streng = deckung_mit_zeitpunkt(gold, vorhergesagt)
        eintraege.append(
            {
                "record_id": rid,
                "goldzellen": len(gold),
                "adressiert": adressiert,
                "adressiert_streng": adressiert_streng,
                "wertgleich": wertgleich,
                "wertgleich_streng": wertgleich_streng,
                "aufblaehung": adressiert - adressiert_streng,
                "zellen": len(vorhergesagt),
                "zellen_eindeutig": len({(*schluessel(z), zeitpunkt(z)) for z in vorhergesagt}),
                "zeitpunkt_mehrdeutig": mehrdeutig(vorhergesagt),
                "zellen_mit_zeitpunkt": sum(1 for z in vorhergesagt if zeitpunkt(z) != "ohne"),
            }
        )

    def s(feld: str) -> int:
        return sum(e[feld] for e in eintraege)

    verteilung = Counter(e["aufblaehung"] for e in eintraege)
    return {
        "modell": MODELL,
        "zeilen": len(eintraege),
        "zeilen_ohne_gold": sum(1 for e in eintraege if not e["goldzellen"]),
        "goldzellen": s("goldzellen"),
        "adressiert": s("adressiert"),
        "adressiert_streng": s("adressiert_streng"),
        "aufblaehung": s("aufblaehung"),
        "wertgleich": s("wertgleich"),
        "wertgleich_streng": s("wertgleich_streng"),
        "wertgleich_aufblaehung": s("wertgleich") - s("wertgleich_streng"),
        "betroffene_zeilen": sum(1 for e in eintraege if e["aufblaehung"] > 0),
        "zellen": s("zellen"),
        "zellen_eindeutig": s("zellen_eindeutig"),
        "zellen_mit_zeitpunkt": s("zellen_mit_zeitpunkt"),
        "zeitpunkt_mehrdeutig": s("zeitpunkt_mehrdeutig"),
        "verteilung": {str(k): v for k, v in sorted(verteilung.items())},
        "groesste": sorted(eintraege, key=lambda e: (-e["aufblaehung"], e["record_id"]))[:10],
        "eintraege": eintraege,
    }


def bericht(werte: dict[str, Any]) -> str:
    quote = werte["aufblaehung"] / werte["adressiert"] if werte["adressiert"] else 0.0
    zeilen = [
        "# Aufblähung der Feld/Arm-Zählung (Lesekopie, 559 erfolgreiche Zeilen)",
        "",
        f"Offline gemessen an {werte['zeilen']} erfolgreichen `{MODELL}`-Zeilen mit "
        "Zellen. Großzügig heißt: Feld und Arm genügen. Streng heißt: derselbe "
        "Feld/Arm-Schlüssel darf nur einen Zeitpunkt nennen.",
        "",
        "| Größe | Wert |",
        "|---|---|",
        f"| Zeilen | {werte['zeilen']} |",
        f"| Goldzellen | {werte['goldzellen']} |",
        f"| adressiert, großzügig | {werte['adressiert']} |",
        f"| adressiert, streng | {werte['adressiert_streng']} |",
        f"| **Aufblähung** | **{werte['aufblaehung']}** "
        f"({quote:.1%} der großzügig adressierten) |",
        f"| wertgleich, großzügig | {werte['wertgleich']} |",
        f"| wertgleich, streng | {werte['wertgleich_streng']} |",
        f"| Aufblähung wertgleich | {werte['wertgleich_aufblaehung']} |",
        f"| betroffene Zeilen | {werte['betroffene_zeilen']} von {werte['zeilen']} |",
        f"| Zellen insgesamt | {werte['zellen']} |",
        f"| davon eindeutig (Feld, Arm, Zeitpunkt) | {werte['zellen_eindeutig']} |",
        f"| Zellen mit Zeitpunkt | {werte['zellen_mit_zeitpunkt']} |",
        f"| Feld/Arm-Gruppen mit mehreren Zeitpunkten | {werte['zeitpunkt_mehrdeutig']} |",
        "",
        "## Verteilung der Aufblähung je Zeile",
        "",
        "| Aufblähung | Zeilen |",
        "|---|---|",
    ]
    for schluessel_wert, anzahl in werte["verteilung"].items():
        zeilen.append(f"| {schluessel_wert} | {anzahl} |")
    if werte["groesste"]:
        zeilen += [
            "",
            "## Zeilen mit der größten Aufblähung",
            "",
            "| Record | Goldzellen | adressiert | streng | Aufblähung | Zellen |",
            "|---|---|---|---|---|---|",
        ]
        for e in werte["groesste"]:
            if e["aufblaehung"] <= 0:
                break
            zeilen.append(
                f"| `{e['record_id']}` | {e['goldzellen']} | {e['adressiert']} | "
                f"{e['adressiert_streng']} | {e['aufblaehung']} | {e['zellen']} |"
            )
    zeilen += [
        "",
        "## Grenze dieser Zahl",
        "",
        "Die Aufblähung ist eine **Untergrenze**, keine Obergrenze: geprüft wird nur, "
        "ob eine Vorhersage denselben Feld/Arm-Schlüssel über mehrere Zeitpunkte "
        "streut. Ob der genannte Zeitpunkt der richtige ist, lässt sich am Gold "
        "nicht prüfen, weil keine Goldzelle einen trägt. Eine Vorhersage, die den "
        f"falschen Zeitpunkt nennt, aber nur einen, zählt hier als Treffer; "
        f"{werte['zellen_mit_zeitpunkt']} von {werte['zellen']} Zellen nennen "
        "überhaupt einen Zeitpunkt. Die tatsächliche Aufblähung kann also größer "
        "sein, nicht kleiner.",
    ]
    if werte["zeilen_ohne_gold"]:
        zeilen += [
            "",
            f"{werte['zeilen_ohne_gold']} erfolgreiche Zeilen haben keine Goldzellen und "
            "können nichts adressieren; sie stehen in den Summen mit 0.",
        ]
    return "\n".join(zeilen) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quelle", default=str(LESEKOPIE))
    parser.add_argument("--records", default=str(RECORDS))
    parser.add_argument("--json", default=str(BENCH / "iterativ" / "ergebnisse" / "aufblaehung_20261118.json"))
    parser.add_argument("--md", default=str(BENCH / "iterativ" / "ergebnisse" / "aufblaehung_20261118.md"))
    args = parser.parse_args()

    records = {r["record_id"]: r for r in lade(Path(args.records))}
    werte = messe(lade(Path(args.quelle)), records)
    if not werte["zeilen"]:
        print(f"FEHLER: keine erfolgreichen Zeilen mit Zellen in {args.quelle}")
        return 2

    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(werte, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.md).write_text(bericht(werte), encoding="utf-8")
    print(bericht(werte))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
