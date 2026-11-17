#!/usr/bin/env python3
"""Gegentest für die Sperrliste in scripts/build_export.py.

Prüft positiv und negativ: bekannte Formulierungen der alten Forschungsagenda
und der privaten Infrastruktur müssen erkannt werden, harmloser Text nicht.
Zusätzlich ein echter Mini-Export, bei dem die gesperrte Datei im Ziel fehlen
muss.

Aufruf:
    python scripts/pruefe_sperrliste.py
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

HIER = Path(__file__).resolve().parent
MODUL = HIER / "build_export.py"
REMOTE = "https://example.invalid/gegentest.git"

# Absichtlich als Daten geprüft, nicht als Prosa: die Prüfzeilen stehen
# zusammengesetzt, damit dieser Test nicht selbst als Treffer zählt.
FAELLE = [
    ("herit" + "ability of the trait", "Alte Forschungsagenda"),
    ("embr" + "yo selection rate", "Alte Forschungsagenda"),
    ("poly" + "genic score", "Alte Forschungsagenda"),
    ("PGT" + "-A cases", "Alte Forschungsagenda"),
    ("Pold" + "erman pooled estimate", "Alte Forschungsagenda"),
    ("loss of function, Wil" + "son effect", "Alte Forschungsagenda (Wilson)"),
    ("tunnel via ng" + "rok", "Private Infrastruktur"),
    ("host 192" + ".168.1.20", "Private Infrastruktur"),
]
SAUBER = [
    "meta-analysis of caffeine on reaction time",
    "Hypertonie und Kochsalzaufnahme in Beobachtungsstudien",
    "der Bericht nennt keinen Kennwert",
]


def lade_export():
    spec = importlib.util.spec_from_file_location("build_export", MODUL)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def pruefe_muster(export) -> int:
    fehler = 0
    for text, kategorie in FAELLE:
        treffer = export.finde_sperrbegriffe(text)
        bewertung = [(name, zeile) for name, zeile, _ in treffer]
        if not treffer:
            print(f"FAIL: nicht erkannt ({kategorie}): {text!r}")
            fehler += 1
        elif treffer[0][0] != kategorie:
            print(f"FAIL: falsche Kategorie für {text!r}: {treffer[0][0]}")
            fehler += 1
        else:
            print(f"OK: erkannt als {kategorie}: {bewertung[0][1]}: {text!r}")
    for text in SAUBER:
        if export.finde_sperrbegriffe(text):
            print(f"FAIL: falsch positiv: {text!r}")
            fehler += 1
        else:
            print(f"OK: kein Treffer: {text!r}")
    return fehler


def pruefe_export(export) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        quelle = Path(tmp) / "quelle"
        ziel = Path(tmp) / "ziel"
        quelle.mkdir()
        dateien = {
            "sauber.py": "print('harmlos')\n",
            "alt_thema.md": "Abschnitt zur " + "herit" + "ability im Tierbefund\n",
            "infra.py": "server = 'https://" + "ngr" + "ok.io'\n",
            "export_allowlist.txt": (
                "export_allowlist.txt\nsauber.py\nalt_thema.md\ninfra.py\n"
            ),
        }
        for name, inhalt in dateien.items():
            (quelle / name).write_text(inhalt, encoding="utf-8")
        for schritt in (
            ("init", "-q"),
            ("add", "-A"),
            ("commit", "-q", "-m", "Gegentest"),
        ):
            subprocess.run(["git", *schritt], cwd=quelle, check=True)

        print("--- Mini-Export ---")
        export.build(quelle, ziel, REMOTE, nachpruefen=False)

        erzeugt = sorted(p.name for p in ziel.iterdir() if p.is_file())
        fehler = 0
        if "sauber.py" not in erzeugt:
            print(f"FAIL: saubere Datei fehlt im Ziel: {erzeugt}")
            fehler += 1
        for gesperrt in ("alt_thema.md", "infra.py"):
            if gesperrt in erzeugt:
                print(f"FAIL: gesperrte Datei wurde kopiert: {gesperrt}")
                fehler += 1
            else:
                print(f"OK: nicht kopiert: {gesperrt}")
        if fehler == 0:
            print(f"OK: Ziel enthält nur {erzeugt}")

        print("--- Streng-Modus ---")
        ziel_streng = Path(tmp) / "ziel_streng"
        try:
            export.build(quelle, ziel_streng, REMOTE, streng=True, nachpruefen=False)
        except SystemExit as exc:
            if exc.code == 1 and not ziel_streng.exists():
                print("OK: --streng bricht ab, bevor das Ziel entsteht")
            else:
                print(f"FAIL: Abbruch mit unerwartetem Zustand: {exc.code}")
                fehler += 1
        else:
            print("FAIL: --streng hat nicht abgebrochen")
            fehler += 1
        return fehler


def main() -> int:
    export = lade_export()
    print("--- Mustererkennung ---")
    fehler = pruefe_muster(export)
    fehler += pruefe_export(export)
    if fehler:
        print(f"GEGENTEST FEHLGESCHLAGEN: {fehler} Abweichungen", file=sys.stderr)
        return 1
    print("GEGENTEST OK: Sperrliste erkennt alle Fälle, Export lässt sie aus")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
