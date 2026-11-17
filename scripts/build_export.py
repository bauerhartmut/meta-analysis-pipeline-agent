#!/usr/bin/env python3
"""Baut einen frischen Export ausschließlich aus der Export-Allowlist.

Jedes Kandidatenfile wird zusätzlich gegen die Sperrbegriffe der alten
Forschungsagenda und der privaten Infrastruktur geprüft. Treffer werden
nicht kopiert und am Ende gemeldet; mit --streng bricht der Lauf ab.

Mit --scan läuft nur die Prüfung: alle getrackten Textdateien eines Baums,
ohne Allowlist und ohne Export. Exitcode 1 bei Treffern; Dateien, deren
Sperrbegriff in einer Ausnahmeliste begründet ist, zählen nicht.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

HIER = Path(__file__).resolve().parent
if str(HIER) not in sys.path:
    sys.path.insert(0, str(HIER))

from export_regeln import BANNED_TERMS, finde_sperrbegriffe  # noqa: E402

DEFAULT_SOURCE = Path(__file__).resolve().parents[1]
ALLOWLIST_NAME = "export_allowlist.txt"
SKIP_SUFFIXES = {
    ".pdf", ".zip", ".db", ".sqlite", ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".docx", ".xlsx", ".parquet", ".pyc", ".log", ".bak", ".woff", ".woff2",
}
COMMIT_MESSAGE = """Kuratierter Quellcode-Export des Research-Agenten

Enthält ausschließlich die in export_allowlist.txt freigegebenen Dateien
ohne Sperrbegriffe der alten Forschungsagenda oder privater Infrastruktur.
Daten, Volltexte, Run-Ordner und geschützte Kernmodule sind nicht enthalten.

🤖 Generated with Codebuff
Co-Authored-By: Codebuff <noreply@codebuff.com>
"""

# Sperrbegriffe: die Liste steht in scripts/export_regeln.py, damit Export-Gate
# und Exporter dieselbe Quelle benutzen.


def fingerabdruck(auszuege: list[str]) -> str:
    """Hash der Trefferzeilen einer Datei (sortiert, whitespace-normalisiert).

    Neue oder geänderte Treffer ändern den Hash; Zeilennummern zählen nicht
    mit, damit ein reines Verschieben den Fingerabdruck nicht kippt.
    """
    zeilen = sorted({" ".join(auszug.split()) for auszug in auszuege})
    hasher = hashlib.sha256()
    for zeile in zeilen:
        hasher.update(zeile.encode("utf-8") + b"\n")
    return hasher.hexdigest()[:16]


def lade_ausnahmen(
    pfad: Path, mit_fingerabdruck: bool = True
) -> dict[str, tuple[str, str]]:
    """Liest `pfad | Begruendung | Fingerabdruck`-Zeilen.

    Jede Ausnahme braucht einen Grund; im Scan zusätzlich den Fingerabdruck
    der Treffer, damit eine gelistete Datei nicht unbemerkt neue Treffer
    bekommen kann.
    """
    if not pfad.is_file():
        raise SystemExit(f"FEHLER: Ausnahmeliste fehlt: {pfad}")
    ausnahmen: dict[str, tuple[str, str]] = {}
    for nummer, roh in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1):
        zeile = roh.strip()
        if not zeile or zeile.startswith("#"):
            continue
        teile = [teil.strip() for teil in zeile.split("|")]
        if len(teile) < 2 or not teile[0] or not teile[1]:
            raise SystemExit(
                f"FEHLER: {pfad}:{nummer}: Ausnahme ohne Begruendung "
                "(Format: pfad | Grund | Fingerabdruck)"
            )
        rel, grund = teile[0], teile[1]
        abdruck = teile[2] if len(teile) > 2 else ""
        if mit_fingerabdruck and len(abdruck) != 16:
            raise SystemExit(
                f"FEHLER: {pfad}:{nummer}: Fingerabdruck fehlt oder ist ungueltig "
                "(16 Hexzeichen; Liste mit --ausnahmen-aktualisieren ergaenzen)"
            )
        ausnahmen[rel] = (grund, abdruck)
    return ausnahmen


def schreibe_ausnahmen(
    pfad: Path, ausnahmen: dict[str, tuple[str, str]]
) -> None:
    """Schreibt die Liste neu, Kopfkommentare bleiben erhalten."""
    kopf = [
        zeile
        for zeile in pfad.read_text(encoding="utf-8").splitlines()
        if zeile.strip().startswith("#") or not zeile.strip()
    ]
    rumpf = [
        f"{rel} | {grund} | {abdruck}"
        for rel, (grund, abdruck) in sorted(ausnahmen.items())
    ]
    pfad.write_text("\n".join(kopf + rumpf) + "\n", encoding="utf-8")


def git(*args: str, cwd: Path) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=cwd, text=True, encoding="utf-8"
    ).strip()


def load_allowlist(source: Path) -> list[str]:
    path = source / ALLOWLIST_NAME
    if not path.is_file():
        raise SystemExit(f"FEHLER: {path} fehlt")
    patterns = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not patterns:
        raise SystemExit(f"FEHLER: {path} enthält keine Regeln")
    return patterns


def matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def source_files(source: Path) -> list[str]:
    return [line for line in git("ls-files", cwd=source).splitlines() if line]


def ist_env_datei(rel: str) -> bool:
    name = Path(rel).name
    return name == ".env" or (name.startswith(".env.") and name != ".env.example")


def filtere_gesperrte(
    source: Path, files: list[str]
) -> tuple[list[str], list[tuple[str, str, int, str]]]:
    """Teilt die Kandidaten in (erlaubt, gesperrt) anhand der Sperrbegriffe."""
    erlaubt: list[str] = []
    gesperrt: list[tuple[str, str, int, str]] = []
    for rel in files:
        path = source / rel
        if ist_env_datei(rel) or path.suffix.lower() in SKIP_SUFFIXES:
            erlaubt.append(rel)
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            erlaubt.append(rel)
            continue
        treffer = finde_sperrbegriffe(text)
        if treffer:
            for kategorie, zeile, auszug in treffer:
                gesperrt.append((rel, kategorie, zeile, auszug))
        else:
            erlaubt.append(rel)
    return erlaubt, gesperrt


def scan(
    source: Path,
    detail: bool = False,
    ausnahmen: dict[str, tuple[str, str]] | None = None,
) -> int:
    """Prüft alle getrackten Textdateien auf Sperrbegriffe, ohne Allowlist.

    Eine Datei aus der Ausnahmeliste gilt nur als begründet, wenn der
    Fingerabdruck ihrer Trefferzeilen zur Liste passt. Weicht er ab, ist die
    Datei offen: irgendetwas ist hinzugekommen und braucht eine Entscheidung.
    Rückgabe ist der Exitcode: 0 ohne offene Treffer, 1 mit Treffern.
    """
    ausnahmen = ausnahmen or {}
    if not source.is_dir():
        raise SystemExit(f"FEHLER: Quelle fehlt: {source}")
    dateien = source_files(source)
    kandidaten = [
        rel
        for rel in dateien
        if Path(rel).suffix.lower() not in SKIP_SUFFIXES and not ist_env_datei(rel)
    ]
    _, gesperrt = filtere_gesperrte(source, kandidaten)
    pro_datei: dict[str, list[tuple[str, int, str]]] = {}
    for rel, kategorie, zeile, auszug in gesperrt:
        pro_datei.setdefault(rel, []).append((kategorie, zeile, auszug))

    aktuell = {rel: fingerabdruck([a for _, _, a in treffer]) for rel, treffer in pro_datei.items()}
    begruendet: list[str] = []
    geaendert: list[str] = []
    offen: list[str] = []
    for rel in pro_datei:
        if rel not in ausnahmen:
            offen.append(rel)
            continue
        _, abdruck = ausnahmen[rel]
        if abdruck == aktuell[rel]:
            begruendet.append(rel)
        else:
            geaendert.append(rel)
            offen.append(rel)

    print(f"Sperrbegriff-Scan ohne Allowlist: {source}")
    print(f"Getrackte Dateien: {len(dateien)}, gescannte Textdateien: {len(kandidaten)}")
    if begruendet:
        print(f"Ausgenommen laut Liste: {len(begruendet)} Dateien (Fingerabdruck passt)")
        if detail:
            for rel in sorted(begruendet):
                print(f"  ~ {rel}: {ausnahmen[rel][0]}")
    if not offen:
        print("Keine offenen Sperrbegriffe gefunden")
        return 0

    print(f"Offene Treffer: {len(offen)} Dateien, {sum(len(pro_datei[r]) for r in offen)} Zeilen")
    for kategorie, anzahl in Counter(
        k for rel in offen for k, _, _ in pro_datei[rel]
    ).most_common():
        print(f"  {kategorie}: {anzahl}")
    for rel in sorted(offen, key=lambda r: (-len(pro_datei[r]), r)):
        if rel in geaendert:
            print(
                f"- {rel}: {len(pro_datei[rel])} Zeilen "
                f"(Fingerabdruck geaendert: Liste {ausnahmen[rel][1]}, jetzt {aktuell[rel]})"
            )
        else:
            print(f"- {rel}: {len(pro_datei[rel])} Zeilen (nicht in der Ausnahmeliste)")
        if detail:
            for kategorie, zeile, auszug in pro_datei[rel]:
                print(f"    {zeile}: {kategorie}: {auszug}")
    return 1


def aktualisiere_ausnahmen(
    source: Path,
    pfad: Path,
    ausnahmen: dict[str, tuple[str, str]],
) -> int:
    """Schreibt die Fingerabdrücke der gelisteten Dateien neu.

    Die Begründungen bleiben unangetastet; Dateien mit Treffern, die nicht in
    der Liste stehen, werden nur gemeldet und nicht automatisch aufgenommen.
    """
    dateien = source_files(source)
    kandidaten = [
        rel
        for rel in dateien
        if Path(rel).suffix.lower() not in SKIP_SUFFIXES and not ist_env_datei(rel)
    ]
    _, gesperrt = filtere_gesperrte(source, kandidaten)
    pro_datei: dict[str, list[tuple[str, int, str]]] = {}
    for rel, kategorie, zeile, auszug in gesperrt:
        pro_datei.setdefault(rel, []).append((kategorie, zeile, auszug))

    neu = dict(ausnahmen)
    for rel, treffer in pro_datei.items():
        if rel in neu:
            grund, _ = neu[rel]
            neu[rel] = (grund, fingerabdruck([a for _, _, a in treffer]))
    # Eintraege ohne Treffer sind erledigt: die Datei ist bereinigt.
    entfernt = sorted(rel for rel in neu if rel not in pro_datei)
    for rel in entfernt:
        del neu[rel]
    schreibe_ausnahmen(pfad, neu)

    print(f"Fingerabdruecke aktualisiert: {len(neu)} Eintraege in {pfad}")
    for rel in entfernt:
        print(f"- Eintrag entfernt (keine Treffer mehr): {rel}")
    unbegruendet = sorted(rel for rel in pro_datei if rel not in neu)
    if unbegruendet:
        print("Ohne Begruendung (bitte von Hand eintragen):")
        for rel in unbegruendet:
            print(f"- {rel}: {len(pro_datei[rel])} Zeilen")
        return 1
    print("Alle Trefferdateien sind begruendet")
    return 0


def build(
    source: Path,
    destination: Path,
    remote_url: str,
    streng: bool = False,
    nachpruefen: bool = True,
) -> None:
    if not source.is_dir():
        raise SystemExit(f"FEHLER: Quelle fehlt: {source}")
    if destination.exists():
        raise SystemExit(f"FEHLER: Ziel existiert bereits: {destination}")
    if destination == source or source in destination.parents:
        raise SystemExit("FEHLER: Ziel darf nicht innerhalb der Quelle liegen")

    patterns = load_allowlist(source)
    files = source_files(source)
    rejected = [rel for rel in files if not matches(rel, patterns)]
    if rejected:
        print("FEHLER: Nicht von der Allowlist erlaubte Quelldateien:", file=sys.stderr)
        for rel in rejected:
            print(f"- {rel}", file=sys.stderr)
        raise SystemExit(1)

    erlaubt, gesperrt = filtere_gesperrte(source, files)
    if gesperrt:
        print(
            f"SPERRBEGRIFFE GEFUNDEN: {len({rel for rel, *_ in gesperrt})} Dateien, "
            f"{len(gesperrt)} Zeilen",
            file=sys.stderr,
        )
        for rel, kategorie, zeile, _ in gesperrt:
            print(f"- {rel}:{zeile}: {kategorie}", file=sys.stderr)
        if streng:
            raise SystemExit(1)
        print("Diese Dateien werden nicht exportiert.", file=sys.stderr)

    destination.mkdir(parents=True)
    for rel in erlaubt:
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, target)

    git("init", "-q", cwd=destination)
    git("add", "-A", cwd=destination)
    git("commit", "-q", "-m", COMMIT_MESSAGE, cwd=destination)
    git("remote", "add", "origin", remote_url, cwd=destination)

    print(f"Export gebaut: {destination}")
    print(f"Dateien: {len(erlaubt)} von {len(files)} (ausgelassen: {len(files) - len(erlaubt)})")
    print(f"Remote: {remote_url}")

    if not nachpruefen:
        return
    check = subprocess.run(
        [sys.executable, "scripts/check_export.py"], cwd=destination, text=True
    )
    if check.returncode:
        raise SystemExit(check.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Baut einen frischen Export aus der Allowlist ohne Sperrbegriffe."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Quell-Repository (Standard: Elternverzeichnis dieses Skripts)",
    )
    parser.add_argument(
        "--dest", type=Path, help="Noch nicht vorhandenes Zielverzeichnis (Pflicht ohne --scan)"
    )
    parser.add_argument(
        "--remote-url", help="Explizite Remote-URL für den neuen Export (Pflicht ohne --scan)"
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Nur Sperrbegriffe prüfen: keine Allowlist, kein Export; Exitcode 1 bei Treffern",
    )
    parser.add_argument(
        "--detail",
        action="store_true",
        help="Mit --scan jede Trefferzeile und jede Ausnahme ausgeben",
    )
    parser.add_argument(
        "--ausnahmen",
        type=Path,
        help="Ausnahmeliste (`pfad | Grund | Fingerabdruck`) für begründete Treffer",
    )
    parser.add_argument(
        "--ausnahmen-aktualisieren",
        action="store_true",
        help="Fingerabdruecke der gelisteten Dateien neu schreiben (mit --scan)",
    )
    parser.add_argument(
        "--streng",
        action="store_true",
        help="Abbruch bei Sperrbegriffen statt Auslassen",
    )
    parser.add_argument(
        "--ohne-nachpruefung",
        action="store_true",
        help="check_export.py im Ziel nicht ausführen (für Gegentests)",
    )
    args = parser.parse_args()
    if args.scan:
        if args.dest or args.remote_url:
            parser.error("--scan arbeitet ohne --dest und --remote-url")
        if args.ausnahmen_aktualisieren:
            if not args.ausnahmen:
                parser.error("--ausnahmen-aktualisieren braucht --ausnahmen")
            return aktualisiere_ausnahmen(
                args.source.resolve(),
                args.ausnahmen,
                lade_ausnahmen(args.ausnahmen, mit_fingerabdruck=False),
            )
        ausnahmen = lade_ausnahmen(args.ausnahmen) if args.ausnahmen else {}
        return scan(args.source.resolve(), detail=args.detail, ausnahmen=ausnahmen)
    if args.ausnahmen or args.ausnahmen_aktualisieren:
        parser.error("--ausnahmen gilt nur zusammen mit --scan")
    if not args.dest or not args.remote_url:
        parser.error("--dest und --remote-url sind ohne --scan Pflicht")
    build(
        args.source.resolve(),
        args.dest.resolve(),
        args.remote_url,
        streng=args.streng,
        nachpruefen=not args.ohne_nachpruefung,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
