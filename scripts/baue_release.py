#!/usr/bin/env python3
"""Baut das oeffentliche Release-Repository ausschliesslich aus `public/`.

Zwei Zonen, eine Regel:

* `public/`     wird veroeffentlicht. Alles darin landet 1:1 im Release.
* alles andere  wird nie veroeffentlicht. Dieses Skript liest keine andere
                Quelle, also kann auch versehentlich nichts mitwandern.

Der fruehere Exporter arbeitete mit einer Allowlist ueber den ganzen Baum und
verlangte, dass *jede* getrackte Datei darin steht. Dadurch landeten private
Skripte in der Liste und damit im oeffentlichen Repo. Diese Fassung kennt nur
noch einen Ordner.

Aufruf:
    python scripts/baue_release.py --pruefen
    python scripts/baue_release.py --bauen --remote-url <url>
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

QUELLE = Path(__file__).resolve().parents[1]
ZONE = QUELLE / "public"
ZIEL_STANDARD = QUELLE / "_release"
SCANNER = ZONE / "scripts" / "pruefe_sperrbegriffe.py"
NOREPLY = "162105560+bauerhartmut@users.noreply.github.com"
MAX_BYTES = 2 * 1024 * 1024
COMMIT = """Oeffentliche Architektur und Messergebnisse

Enthaelt ausschliesslich den Inhalt von public/: Architekturbeschreibung,
Benchmark-Ergebnisse und den Sperrbegriff-Scan. Kein Harness-Code, keine
Daten, keine Rohlaeufe.

🤖 Generated with Codebuff
Co-Authored-By: Codebuff <noreply@codebuff.com>
"""


def git(*args: str, cwd: Path) -> str:
    ergebnis = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if ergebnis.returncode:
        raise SystemExit(f"FEHLER: git {' '.join(args)}: {ergebnis.stderr.strip()}")
    return ergebnis.stdout.strip()


def zone_dateien() -> list[str]:
    """Alle in `public/` getrackten Dateien, relativ zum Ordner."""
    roh = subprocess.run(
        ["git", "ls-files", "-z", "--", "public"], cwd=QUELLE,
        capture_output=True, text=True, encoding="utf-8",
    )
    if roh.returncode:
        raise SystemExit(f"FEHLER: git ls-files: {roh.stderr.strip()}")
    pfade = [p for p in roh.stdout.split("\0") if p]
    if not pfade:
        raise SystemExit("FEHLER: public/ enthaelt keine getrackten Dateien")
    return [Path(p).relative_to("public").as_posix() for p in pfade]


def pruefe_zone() -> int:
    """Scannt den Ordner public/ auf Sperrbegriffe, Secrets und Uebergroessen."""
    dateien = zone_dateien()
    befunde: list[str] = []
    for rel in dateien:
        pfad = ZONE / rel
        if pfad.stat().st_size > MAX_BYTES:
            befunde.append(f"{rel}: groesser als {MAX_BYTES // 1024 // 1024} MiB")
    # Geprueft wird nur die Zone: der Scanner listet die getrackten Dateien des
    # Verzeichnisses, in dem er laeuft.
    lauf = subprocess.run(
        [sys.executable, str(SCANNER), "--nur-baum"], cwd=ZONE,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print(lauf.stdout.strip())
    print(f"Dateien in public/: {len(dateien)}")
    if lauf.returncode or befunde:
        for zeile in befunde:
            print(f"- {zeile}")
        print("\nAbbruch: public/ ist nicht veroeffentlichbar.")
        return 1
    return 0


def baue(ziel: Path, remote_url: str, repo_name: str) -> int:
    if ziel.exists():
        raise SystemExit(f"FEHLER: Ziel existiert bereits: {ziel} (vorher loeschen)")
    dateien = zone_dateien()
    ziel.mkdir(parents=True)
    for rel in dateien:
        kopie = ziel / rel
        kopie.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ZONE / rel, kopie)

    git("init", "-q", cwd=ziel)
    git("symbolic-ref", "HEAD", "refs/heads/master", cwd=ziel)
    git("config", "user.name", "Bauer Hartmut", cwd=ziel)
    git("config", "user.email", NOREPLY, cwd=ziel)
    git("config", "core.hooksPath", ".githooks", cwd=ziel)
    git("add", "-A", cwd=ziel)
    git("commit", "-q", "-m", COMMIT, cwd=ziel)
    git("remote", "add", "origin", remote_url, cwd=ziel)

    print(f"\nRelease gebaut: {ziel}  ({len(dateien)} Dateien)")
    print(f"Remote: {remote_url}")

    # Zweite Stufe: der gebaute Stand muss auch vor der Historie bestehen.
    nach = subprocess.run(
        [sys.executable, "scripts/pruefe_sperrbegriffe.py"], cwd=ziel,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print(nach.stdout.strip())
    if nach.returncode:
        print(f"\nAbbruch: gebauter Stand {repo_name} besteht den Scan nicht.")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Release aus public/ bauen.")
    parser.add_argument("--pruefen", action="store_true", help="nur public/ scannen")
    parser.add_argument("--bauen", action="store_true", help="Release bauen")
    parser.add_argument("--ziel", type=Path, default=ZIEL_STANDARD)
    parser.add_argument("--remote-url")
    parser.add_argument("--repo-name", default="meta-analysis-pipeline-agent")
    args = parser.parse_args()

    if args.pruefen == args.bauen:
        parser.error("genau eins von --pruefen oder --bauen")
    if args.pruefen:
        return pruefe_zone()
    if not args.remote_url:
        parser.error("--remote-url ist Pflicht beim Bauen")
    return baue(args.ziel.resolve(), args.remote_url, args.repo_name)


if __name__ == "__main__":
    raise SystemExit(main())
