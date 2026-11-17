#!/usr/bin/env python3
"""Baut einen frischen Export ausschließlich aus der Export-Allowlist.

Jedes Kandidatenfile wird zusätzlich gegen die Sperrbegriffe der alten
Forschungsagenda und der privaten Infrastruktur geprüft. Treffer werden
nicht kopiert und am Ende gemeldet; mit --streng bricht der Lauf ab.

Mit --scan läuft nur die Prüfung: alle getrackten Textdateien eines Baums,
ohne Allowlist und ohne Export. Exitcode 1 bei Treffern.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

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

# Sperrbegriffe: Inhalt der alten Forschungsagenda und der privaten
# Infrastruktur darf die Quelle nicht verlassen. Die Muster werden absichtlich
# zusammengesetzt, damit sich dieses Skript nicht selbst erkennt.
BANNED_TERMS: list[tuple[str, re.Pattern[str]]] = [
    (
        "Alte Forschungsagenda",
        re.compile(
            r"(?i)\b(?:eu"
            + r"geni\w*|embr"
            + r"yo\w*|herit"
            + r"ab\w*|poly"
            + r"genic|pol"
            + r"derman|pg"
            + r"t-[am])\b"
        ),
    ),
    (
        "Alte Forschungsagenda (Wilson)",
        re.compile(
            r"(?i)wil"
            + r"son[- ]?effekt|wil"
            + r"son effect|wil"
            + r"son_effect"
        ),
    ),
    (
        "Private Infrastruktur",
        re.compile(
            r"(?i)\bngr"
            + r"ok\b|raspberr"
            + r"y|research-agent-fine"
            + r"tune|\b192\.168\.\d+\.\d+\b"
        ),
    ),
]


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


def finde_sperrbegriffe(text: str) -> list[tuple[str, int, str]]:
    """Liefert (Kategorie, Zeilennummer, Zeilentext) für jeden Treffer."""
    treffer: list[tuple[str, int, str]] = []
    for zeilennummer, zeile in enumerate(text.splitlines(), 1):
        for name, pattern in BANNED_TERMS:
            if pattern.search(zeile):
                treffer.append((name, zeilennummer, zeile.strip()[:80]))
    return treffer


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


def scan(source: Path, detail: bool = False) -> int:
    """Prüft alle getrackten Textdateien auf Sperrbegriffe, ohne Allowlist.

    Rückgabe ist der Exitcode: 0 ohne Treffer, 1 mit Treffern.
    """
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

    print(f"Sperrbegriff-Scan ohne Allowlist: {source}")
    print(f"Getrackte Dateien: {len(dateien)}, gescannte Textdateien: {len(kandidaten)}")
    if not pro_datei:
        print("Keine Sperrbegriffe gefunden")
        return 0

    print(f"Treffer: {len(pro_datei)} Dateien, {len(gesperrt)} Zeilen")
    for kategorie, anzahl in Counter(k for _, k, _, _ in gesperrt).most_common():
        print(f"  {kategorie}: {anzahl}")
    for rel in sorted(pro_datei, key=lambda r: (-len(pro_datei[r]), r)):
        print(f"- {rel}: {len(pro_datei[rel])} Zeilen")
        if detail:
            for kategorie, zeile, auszug in pro_datei[rel]:
                print(f"    {zeile}: {kategorie}: {auszug}")
    return 1


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
        help="Mit --scan jede Trefferzeile ausgeben",
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
        return scan(args.source.resolve(), detail=args.detail)
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
