#!/usr/bin/env python
"""Audit: Haben andere Analyse- und Messskripte denselben Trennzeichen-Fehler?

Der alte Zahlvergleich in `falschwert_20261120.py` las `7.69` als 769, weil er
Trennzeichen ohne Pruefung der Gruppengroessen entfernte. Dieses Audit prueft
das repo-weit auf zwei Wegen:

1. Statisch: alle `*.py` nach Mustern durchsuchen, die Trennzeichen entfernen,
   und je Fund die Umgebung daraufhin ansehen, ob eine Gruppierungspruefung
   daneben steht.
2. Dynamisch: die vorhandenen Zahlparser mit denselben Teststrings fuettern und
   ihr Ergebnis gegen die zulaessigen Lesarten halten.

Rein lesend, kein Modellaufruf, kein Netz.

Aufruf:
    .venv/bin/python .../trennzeichen_audit_20261120.py
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent.parent
ROOT = HIER.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BENCH.parent))
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(HIER))

AUSGABE_JSON = HIER / "trennzeichen_audit_20261120.json"
AUSGABE_MD = HIER / "trennzeichen_audit_20261120.md"

#: Teststrings mit den zulaessigen Lesarten. Zwei Lesarten heisst: mehrdeutig,
#: je nach Konvention des Dokuments.
FAELLE: list[tuple[str, set[float], str]] = [
    ("7.69", {7.69}, "der alte Fehler machte daraus 769"),
    ("7,69", {7.69}, "deutsches Dezimalkomma"),
    ("769", {769.0}, "ganze Zahl"),
    ("1,919", {1.919, 1919.0}, "englischer Tausendertrenner oder deutsches Dezimalkomma"),
    ("1.919", {1.919, 1919.0}, "deutscher Tausendertrenner oder Dezimalpunkt"),
    ("1.234,5", {1234.5}, "deutsch: Punkt Tausender, Komma Dezimal"),
    ("1,234.5", {1234.5}, "englisch: Komma Tausender, Punkt Dezimal"),
    ("11,897", {11.897, 11897.0}, "mehrdeutig wie 1,919"),
]

PATTERN = [
    (re.compile(r'replace\(\s*["\']\.["\']\s*,\s*["\']["\']\s*\)\s*\.\s*replace\(\s*["\'],'),
     "Punkt und Komma werden beide entfernt"),
    (re.compile(r're\.sub\(\s*r?["\'][^"\']*\[\.,\s\\\]'),
     "Zeichenklasse mit Trennzeichen in re.sub"),
    (re.compile(r'replace\(\s*["\'],["\']\s*,\s*["\']\.["\']'),
     "Komma wird zu Punkt (Spiegelrichtung)"),
    (re.compile(r'replace\(\s*["\'],["\']\s*,\s*["\']["\']\s*\)'),
     "Komma wird entfernt"),
]

#: Gruppenpruefung in der Naehe eines Fundes.
GRUPPE = re.compile(r"\\d\{1,3\}|fullmatch|\{3\}|count\(\s*[\"'],[\"']\s*\)\s*[>=]")


def parser() -> list[tuple[str, str, Callable[[str], Any]]]:
    """Die vorhandenen Zahlparser, jeder unter seinem Fundort."""
    out: list[tuple[str, str, Callable[[str], Any]]] = []

    def add(datei: str, name: str, funktion: Callable[[str], Any], modul: str = "") -> None:
        out.append((datei, name, funktion, modul or name))

    try:
        from extended_benchmark.iterativ import gemeinsam

        add("public_benchmark/extended_benchmark/iterativ/gemeinsam.py", "als_zahl",
            lambda s: gemeinsam.als_zahl(s), "gemeinsam.als_zahl")
    except Exception as exc:  # noqa: BLE001
        out.append(("gemeinsam", "als_zahl", lambda s: repr(exc), "gemeinsam.als_zahl"))

    try:
        from extended_benchmark.yun_full import werte_p5_aus

        add("public_benchmark/extended_benchmark/yun_full/werte_p5_aus.py", "zahl",
            lambda s: werte_p5_aus.zahl(s), "werte_p5_aus.zahl")
    except Exception as exc:  # noqa: BLE001
        out.append(("werte_p5_aus", "zahl", lambda s: repr(exc), "werte_p5_aus.zahl"))

    try:
        add("public_benchmark/extended_benchmark/analysis/glm53_p5_vergleich_20261120/vergleiche_20261120.py",
            "zahl", lambda s: __import__("vergleiche_20261120").zahl(s), "vergleiche.zahl")
    except Exception as exc:  # noqa: BLE001
        out.append(("vergleiche", "zahl", lambda s: repr(exc), "vergleiche.zahl"))

    try:
        from extended_benchmark.yun_full import baue_yun699

        add("public_benchmark/extended_benchmark/yun_full/baue_yun699.py", "zahl",
            lambda s: baue_yun699.zahl(s)[0], "baue_yun699.zahl")
    except Exception as exc:  # noqa: BLE001
        out.append(("baue_yun699", "zahl", lambda s: repr(exc), "baue_yun699.zahl"))

    try:
        from research_agent.meta import arm_level

        add("research_agent/meta/arm_level.py", "parse_number",
            lambda s: arm_level.parse_number(s), "arm_level.parse_number")
    except Exception as exc:  # noqa: BLE001
        out.append(("arm_level", "parse_number", lambda s: repr(exc), "arm_level.parse_number"))

    try:
        from extended_benchmark import precheck_gold

        add("public_benchmark/extended_benchmark/precheck_gold.py", "zahlen_mit_position",
            lambda s: [w for _, w, _ in precheck_gold.zahlen_mit_position(s)], "precheck_gold")
    except Exception as exc:  # noqa: BLE001
        out.append(("precheck_gold", "zahlen_mit_position", lambda s: repr(exc), "precheck_gold"))

    pfad = ROOT / "scripts" / "pruefe_extraktion_20261109.py"
    if pfad.exists():
        try:
            spec = importlib.util.spec_from_file_location("pruefe_extraktion", pfad)
            modul = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(modul)
            add("scripts/pruefe_extraktion_20261109.py", "zahl",
                lambda s: modul.zahl(s), "pruefe_extraktion.zahl")
        except Exception as exc:  # noqa: BLE001
            out.append(("pruefe_extraktion", "zahl", lambda s: repr(exc), "pruefe_extraktion.zahl"))
    return out


def statisch() -> dict[str, Any]:
    treffer: list[dict[str, Any]] = []
    for pfad in sorted(ROOT.rglob("*.py")):
        # Fremdpakete und Exportkopien zaehlen nicht: sie sind nicht der laufende
        # Code des Projekts und wuerden die Zählung nur verwaessern.
        if any(
            teil in (".git", "node_modules", "__pycache__")
            or str(teil).startswith((".venv", "export_clean", "handoff"))
            for teil in pfad.parts
        ):
            continue
        try:
            zeilen = pfad.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for nummer, zeile in enumerate(zeilen, 1):
            for muster, label in PATTERN:
                if not muster.search(zeile):
                    continue
                umgebung = "\n".join(zeilen[max(0, nummer - 7): nummer + 6])
                treffer.append({
                    "datei": pfad.relative_to(ROOT).as_posix(),
                    "zeile": nummer,
                    "muster": label,
                    "gruppierung_in_umgebung": bool(GRUPPE.search(umgebung)),
                    "text": zeile.strip()[:160],
                })
                break
    return {"anzahl": len(treffer), "treffer": treffer}


def main() -> int:
    statik = statisch()
    dynamik: list[dict[str, Any]] = []
    for datei, name, funktion, label in parser():
        ergebnisse = []
        for text, erlaubt, hinweis in FAELLE:
            try:
                wert = funktion(text)
            except Exception as exc:  # noqa: BLE001
                wert = f"FEHLER {type(exc).__name__}"
            if isinstance(wert, list):
                lesarten = [w for w in wert if isinstance(w, (int, float))]
                ok = bool(lesarten) and all(any(abs(w - e) < 1e-9 for e in erlaubt) for w in lesarten)
            elif isinstance(wert, (int, float)):
                ok = any(abs(wert - e) < 1e-9 for e in erlaubt)
            else:
                ok = False
            ergebnisse.append({
                "eingabe": text,
                "ergebnis": wert if not isinstance(wert, list) else lesarten,
                "zulaessig": sorted(erlaubt),
                "ok": ok,
                "mehrdeutig": len(erlaubt) > 1,
                "hinweis": hinweis,
            })
        fehler = [e for e in ergebnisse if not e["ok"]]
        dynamik.append({
            "datei": datei,
            "funktion": label,
            "ergebnisse": ergebnisse,
            "fehler": len(fehler),
            "urteil": "fehlerhaft" if fehler else "ok",
        })

    ergebnis = {"statisch": statik, "dynamisch": dynamik}
    AUSGABE_JSON.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Trennzeichen-Audit der Analyse- und Messskripte (20.11.2026)",
        "",
        "Anlass: der alte Zahlvergleich in `falschwert_20261120.py` las `7.69` als 769, "
        "weil er Trennzeichen ohne Pruefung der Gruppengroessen entfernte. Geprueft ist, "
        "ob andere Skripte denselben oder den spiegelbildlichen Fehler haben.",
        "",
        "## Dynamisch: vorhandene Parser mit denselben Teststrings",
        "",
        "| Funktion | " + " | ".join(f"`{t}`" for t, _, _ in FAELLE) + " | Urteil |",
        "|---|" + "---|" * len(FAELLE) + "---|",
    ]
    for block in dynamik:
        zellen = []
        for e in block["ergebnisse"]:
            wert = e["ergebnis"]
            if isinstance(wert, list):
                text = ", ".join(str(w) for w in wert) if wert else "-"
            else:
                text = "-" if wert is None else str(wert)
            zellen.append(text + ("" if e["ok"] else " **!**"))
        md.append(f"| `{block['funktion']}` | " + " | ".join(zellen) + f" | {block['urteil']} |")
    md += [
        "",
        "`!` markiert ein Ergebnis ausserhalb der zulaessigen Lesarten. Mehrdeutige "
        "Eingaben (`1,919`, `1.919`, `11,897`) gelten als bestanden, wenn eine der "
        "beiden Konventionen getroffen wird.",
        "",
        "## Statisch: Fundstellen im Repo",
        "",
        f"{statik['anzahl']} Fundstellen in `*.py` (ohne `.venv`). Die Spalte "
        "`Gruppierung` sagt, ob im Umfeld eine Pruefung auf Dreiergruppen steht.",
        "",
        "| Datei | Zeile | Muster | Gruppierung | Code |",
        "|---|---:|---|---|---|",
    ]
    for t in statik["treffer"]:
        code = t["text"].replace("|", "\\|")
        md.append(f"| `{t['datei']}` | {t['zeile']} | {t['muster']} | "
                  f"{'ja' if t['gruppierung_in_umgebung'] else 'nein'} | `{code}` |")
    md.append("")
    AUSGABE_MD.write_text("\n".join(md), encoding="utf-8", newline="\n")

    for block in dynamik:
        print(f"{block['funktion']:<28} Fehler {block['fehler']}  {block['urteil']}")
        for e in block["ergebnisse"]:
            if not e["ok"]:
                print(f"    {e['eingabe']!r} -> {e['ergebnis']} (zulaessig {e['zulaessig']})")
    print("statische Fundstellen:", statik["anzahl"])
    print("geschrieben:", AUSGABE_JSON)
    print("geschrieben:", AUSGABE_MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
