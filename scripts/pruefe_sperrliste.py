#!/usr/bin/env python3
"""Gegentest für die Sperrliste in scripts/build_export.py.

Prüft positiv und negativ: bekannte Formulierungen der alten Forschungsagenda
und der privaten Infrastruktur müssen erkannt werden, harmloser Text nicht.
Dazu ein echter Mini-Export (gesperrte Datei darf im Ziel fehlen), der
Streng-Modus und der Scan-Modus ohne Allowlist mit seinen Exitcodes.

Aufruf:
    python scripts/pruefe_sperrliste.py
"""

from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
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
BEFUNDE = {
    "sauber.py": "print('harmlos')\n",
    "alt_thema.md": "Abschnitt zur " + "herit" + "ability im Tierbefund\n",
    "infra.py": "server = 'https://" + "ngr" + "ok.io'\n",
}


def lade_export():
    spec = importlib.util.spec_from_file_location("build_export", MODUL)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def schreibe_quelle(pfad: Path, dateien: dict[str, str], allowlist: bool) -> None:
    pfad.mkdir(parents=True)
    inhalt = dict(dateien)
    if allowlist:
        inhalt["export_allowlist.txt"] = "\n".join(
            ["export_allowlist.txt", *dateien]
        ) + "\n"
    for name, text in inhalt.items():
        (pfad / name).write_text(text, encoding="utf-8")
    for schritt in (("init", "-q"), ("add", "-A"), ("commit", "-q", "-m", "Gegentest")):
        subprocess.run(["git", *schritt], cwd=pfad, check=True)


def pruefe_muster(export) -> int:
    fehler = 0
    for text, kategorie in FAELLE:
        treffer = export.finde_sperrbegriffe(text)
        if not treffer:
            print(f"FAIL: nicht erkannt ({kategorie}): {text!r}")
            fehler += 1
        elif treffer[0][0] != kategorie:
            print(f"FAIL: falsche Kategorie für {text!r}: {treffer[0][0]}")
            fehler += 1
        else:
            print(f"OK: erkannt als {kategorie}: {text!r}")
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
        schreibe_quelle(quelle, BEFUNDE, allowlist=True)

        print("--- Mini-Export ---")
        with redirect_stdout(io.StringIO()):
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


def pruefe_scan(export) -> int:
    fehler = 0
    with tempfile.TemporaryDirectory() as tmp:
        schmutzig = Path(tmp) / "schmutzig"
        sauber = Path(tmp) / "sauber"
        # Kein export_allowlist.txt: der Scan darf keine Allowlist verlangen.
        schreibe_quelle(schmutzig, BEFUNDE, allowlist=False)
        schreibe_quelle(sauber, {"nur.py": "print('harmlos')\n"}, allowlist=False)

        print("--- Scan-Modus: schmutziger Baum ---")
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            code = export.scan(schmutzig)
        ausgabe = puffer.getvalue()
        if code != 1:
            print(f"FAIL: Scan-Exitcode bei Treffern ist {code}, erwartet 1")
            fehler += 1
        else:
            print("OK: Scan-Exitcode 1 bei Treffern")
        if "alt_thema.md" not in ausgabe or "infra.py" not in ausgabe:
            print(f"FAIL: Trefferdateien fehlen in der Ausgabe:\n{ausgabe}")
            fehler += 1
        else:
            print("OK: beide Trefferdateien werden genannt")
        if "sauber.py" in ausgabe:
            print("FAIL: saubere Datei als Treffer gemeldet")
            fehler += 1
        else:
            print("OK: saubere Datei nicht als Treffer gemeldet")

        print("--- Scan-Modus: Detailausgabe ---")
        detail = io.StringIO()
        with redirect_stdout(detail):
            export.scan(schmutzig, detail=True)
        if "Alte Forschungsagenda" in detail.getvalue() and "Private Infrastruktur" in detail.getvalue():
            print("OK: --detail nennt die Kategorien je Zeile")
        else:
            print(f"FAIL: --detail ohne Kategorien:\n{detail.getvalue()}")
            fehler += 1

        print("--- Scan-Modus: sauberer Baum ---")
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            code = export.scan(sauber)
        if code != 0 or "Keine offenen Sperrbegriffe" not in puffer.getvalue():
            print(f"FAIL: sauberer Baum meldet Code {code}: {puffer.getvalue()!r}")
            fehler += 1
        else:
            print("OK: sauberer Baum, Exitcode 0")

        print("--- Scan-Modus über die Kommandozeile ---")
        lauf = subprocess.run(
            [sys.executable, str(MODUL), "--scan", "--source", str(schmutzig)],
            capture_output=True,
            text=True,
        )
        if lauf.returncode == 1 and "Sperrbegriff-Scan ohne Allowlist" in lauf.stdout:
            print("OK: Kommandozeilen-Scan endet mit 1 und meldet den Modus")
        else:
            print(f"FAIL: Kommandozeilen-Scan: {lauf.returncode}\n{lauf.stdout}\n{lauf.stderr}")
            fehler += 1
        fehlerhaft = subprocess.run(
            [sys.executable, str(MODUL), "--scan", "--dest", str(Path(tmp) / "x")],
            capture_output=True,
            text=True,
        )
        if fehlerhaft.returncode == 2:
            print("OK: --scan zusammen mit --dest wird abgelehnt")
        else:
            print(f"FAIL: unerwarteter Exitcode {fehlerhaft.returncode} für --scan mit --dest")
            fehler += 1
        return fehler


def pruefe_ausnahmen(export) -> int:
    fehler = 0
    with tempfile.TemporaryDirectory() as tmp:
        baum = Path(tmp) / "baum"
        schreibe_quelle(baum, BEFUNDE, allowlist=False)
        liste = Path(tmp) / "ausnahmen.txt"
        liste.write_text(
            "# Kopfzeile\n"
            "alt_thema.md | Testfixture der frueheren Reihe\n"
            "infra.py | Betriebsnotiz des alten Servers\n",
            encoding="utf-8",
        )

        print("--- Ausnahmen: begruendet ---")
        ausnahmen = export.lade_ausnahmen(liste)
        if set(ausnahmen) == {"alt_thema.md", "infra.py"}:
            print("OK: Ausnahmeliste gelesen, Gründe erhalten")
        else:
            print(f"FAIL: Ausnahmeliste falsch gelesen: {ausnahmen}")
            fehler += 1

        puffer = io.StringIO()
        with redirect_stdout(puffer):
            code = export.scan(baum, ausnahmen=ausnahmen)
        ausgabe = puffer.getvalue()
        if code != 0 or "Keine offenen Sperrbegriffe" not in ausgabe:
            print(f"FAIL: begründete Treffer blockieren den Scan: {code}\n{ausgabe}")
            fehler += 1
        elif "Ausgenommen laut Liste: 2 Dateien" not in ausgabe:
            print(f"FAIL: Ausnahmen werden nicht gezählt:\n{ausgabe}")
            fehler += 1
        else:
            print("OK: begründete Treffer blockieren nicht")

        nur_eine = Path(tmp) / "eine.txt"
        nur_eine.write_text("alt_thema.md | Testfixture\n", encoding="utf-8")
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            code = export.scan(baum, ausnahmen=export.lade_ausnahmen(nur_eine))
        if code == 1 and "infra.py" in puffer.getvalue():
            print("OK: nicht gelistete Datei bleibt offener Treffer")
        else:
            print(f"FAIL: nicht gelistete Datei wurde stillschweigend akzeptiert: {puffer.getvalue()}")
            fehler += 1

        print("--- Ausnahmen: fehlende Begruendung ---")
        kaputt = Path(tmp) / "kaputt.txt"
        kaputt.write_text("alt_thema.md\n", encoding="utf-8")
        try:
            export.lade_ausnahmen(kaputt)
        except SystemExit as exc:
            if "ohne Begruendung" in str(exc.code):
                print("OK: Ausnahme ohne Grund wird abgelehnt")
            else:
                print(f"FAIL: Abbruch mit falschem Text: {exc.code}")
                fehler += 1
        else:
            print("FAIL: Ausnahme ohne Grund wurde akzeptiert")
            fehler += 1

        print("--- Ausnahmen über die Kommandozeile ---")
        lauf = subprocess.run(
            [
                sys.executable,
                str(MODUL),
                "--scan",
                "--source",
                str(baum),
                "--ausnahmen",
                str(liste),
                "--detail",
            ],
            capture_output=True,
            text=True,
        )
        if lauf.returncode == 0 and "Testfixture der frueheren Reihe" in lauf.stdout:
            print("OK: CLI-Scan mit Ausnahmen endet mit 0 und zeigt den Grund")
        else:
            print(f"FAIL: CLI mit Ausnahmen: {lauf.returncode}\n{lauf.stdout}\n{lauf.stderr}")
            fehler += 1
        return fehler


def main() -> int:
    export = lade_export()
    print("--- Mustererkennung ---")
    fehler = pruefe_muster(export)
    fehler += pruefe_export(export)
    fehler += pruefe_scan(export)
    fehler += pruefe_ausnahmen(export)
    if fehler:
        print(f"GEGENTEST FEHLGESCHLAGEN: {fehler} Abweichungen", file=sys.stderr)
        return 1
    print(
        "GEGENTEST OK: Sperrliste erkennt alle Fälle, Export lässt sie aus, "
        "Scan findet sie, begründete Ausnahmen zählen nicht"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
