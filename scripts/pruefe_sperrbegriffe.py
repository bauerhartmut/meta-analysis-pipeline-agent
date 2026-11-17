#!/usr/bin/env python3
"""Sperrbegriff- und Secret-Scan fuer dieses Repository: Baum und Historie.

Wird vom pre-push-Hook und vom CI-Job aufgerufen. Es gibt keine Allowlist und
keine Ausnahmen: ein Treffer blockiert. Die Muster sind absichtlich aus
Fragmenten zusammengesetzt, damit dieses Skript sich selbst nicht als Treffer
zaehlt.

Aufruf:
    python scripts/pruefe_sperrbegriffe.py              # Baum + Historie
    python scripts/pruefe_sperrbegriffe.py --nur-baum   # schneller Vorabtest
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

TEXT_SUFFIXES = {
    ".md", ".txt", ".py", ".sh", ".bat", ".yml", ".yaml", ".json", ".csv",
    ".toml", ".cfg", ".ini", ".html", ".css", ".js", ".tex", ".githooks",
}

MUSTER: list[tuple[str, re.Pattern[str]]] = [
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
        re.compile(r"(?i)wil" + r"son[- ]?effekt|wil" + r"son effect|wil" + r"son_effect"),
    ),
    (
        "Private Infrastruktur",
        re.compile(
            r"(?i)\bngr"
            + r"ok\b|raspberr"
            + r"y|research-agent-fine"
            + r"tune|\b192\.168\.\d+\.\d+\b|\b10\.\d+\.\d+\.\d+\b"
        ),
    ),
    (
        "Absoluter Nutzerpfad",
        re.compile(r"[A-Za-z]:\\Users\\|/home/[a-z0-9_-]+/|\bssh -[A-Za-z]* -R\b"),
    ),
    (
        "Secret-Muster",
        re.compile(
            r"(?:sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
            r"|AKIA[0-9A-Z]{16}|xox[baprs]-|AIza[0-9A-Za-z_-]{30,}|hf_[A-Za-z0-9]{20,}"
            r"|-----BEGIN [A-Z ]*PRIVATE KEY|NGROK_AUTH_TOKEN\s*=\s*\S|auth"
            r"token:)"
        ),
    ),
]


def scan_text(text: str) -> list[tuple[str, int, str]]:
    """Liefert (Kategorie, Zeilennummer, Auszug) fuer jeden Treffer."""
    treffer: list[tuple[str, int, str]] = []
    for nummer, zeile in enumerate(text.splitlines(), 1):
        for kategorie, muster in MUSTER:
            if muster.search(zeile):
                treffer.append((kategorie, nummer, zeile.strip()[:90]))
    return treffer


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace"
    ).stdout


def pruefe_baum() -> list[str]:
    """Scannt alle getrackten Textdateien des Arbeitsbaums."""
    befunde: list[str] = []
    for rel in git("ls-files", "-z").split("\0"):
        if not rel:
            continue
        suffix = rel.rsplit(".", 1)[-1].lower() if "." in rel else ""
        if suffix not in {s.lstrip(".") for s in TEXT_SUFFIXES}:
            continue
        try:
            with open(rel, encoding="utf-8") as datei:
                text = datei.read()
        except (OSError, UnicodeDecodeError):
            continue
        for kategorie, nummer, auszug in scan_text(text):
            befunde.append(f"{rel}:{nummer}: {kategorie}: {auszug}")
    return befunde


def pruefe_historie() -> list[str]:
    """Scannt jede erreichbare Fassung jeder Datei in allen Commits.

    Der Baum allein genuegt nicht: eine spaeter geloeschte Datei bleibt in der
    Historie abrufbar. Geprueft wird deshalb jeder Commit einzeln.
    """
    befunde: list[str] = []
    commits = [zeile for zeile in git("rev-list", "--all").splitlines() if zeile]
    for commit in commits:
        ausgabe = subprocess.run(
            ["git", "grep", "-I", "-n", "-E", ".".join(f"(?:{m.pattern})" for _, m in MUSTER),
             commit, "--", "."],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout
        for zeile in ausgabe.splitlines():
            # Format: <commit>:<pfad>:<zeile>:<inhalt>
            teile = zeile.split(":", 3)
            if len(teile) < 4:
                continue
            _, pfad, nummer, inhalt = teile
            for kategorie, muster in MUSTER:
                if muster.search(inhalt):
                    befunde.append(
                        f"{commit[:8]}:{pfad}:{nummer}: {kategorie}: {inhalt.strip()[:90]}"
                    )
                    break
    return befunde


def main() -> int:
    parser = argparse.ArgumentParser(description="Sperrbegriff-Scan ohne Ausnahmen.")
    parser.add_argument("--nur-baum", action="store_true", help="Historie ueberspringen")
    args = parser.parse_args()

    baum = pruefe_baum()
    historie: list[str] = [] if args.nur_baum else pruefe_historie()

    print(f"Arbeitsbaum: {len(baum)} Treffer")
    print(f"Historie:    {len(historie)} Treffer" if not args.nur_baum else "Historie:    uebersprungen")
    offen = baum + historie
    if not offen:
        print("Sauber: keine Sperrbegriffe, keine Secret-Muster.")
        return 0
    for zeile in offen[:50]:
        print(f"- {zeile}")
    if len(offen) > 50:
        print(f"... {len(offen) - 50} weitere")
    print("\nAbbruch: Der Stand ist nicht veroeffentlichbar.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
