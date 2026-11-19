"""Isolierte Tests der Positivkontrolle vor der P5-Auswertung.

Getestet wird `yun_full/werte_p5_mit_kontrolle.sh` mit Stub-Skripten: die
Auswertung ist hier ein Zaehler, der nur eine Datei anlegt. So ist belegbar, ob
sie gerufen wurde oder nicht — ohne Netz, ohne Modell, ohne echte Predictions.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
REPO = BENCH.parent
WRAPPER = BENCH / "extended_benchmark" / "yun_full" / "werte_p5_mit_kontrolle.sh"


def _bash() -> str:
    """Ein Bash, der die Windows-Pfade dieses Repos oeffnen kann.

    `bash` aus einem Windows-Python ist hier ein WSL-Bash und scheitert an
    `D:/...`; msys-Bash oeffnet sie. Deshalb wird der Interpreter geprueft, statt
    dem Namen zu vertrauen.
    """
    for kandidat in (
        os.environ.get("BASH_PFAD"),
        r"C:\msys64\usr\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
    ):
        if not kandidat or not Path(kandidat).exists():
            continue
        pruefung = subprocess.run(
            [kandidat, "-c", f'test -f "{WRAPPER.as_posix()}"'], capture_output=True
        )
        if pruefung.returncode == 0:
            return kandidat
    return "bash"


BASH = _bash()


def _stub_kontrolle(tmp_path: Path, code: int, schreibe_marke: bool) -> Path:
    """Stub, der einen Exitcode liefert und die Marke nur auf Wunsch schreibt."""
    pfad = tmp_path / f"kontrolle_{code}_{int(schreibe_marke)}.py"
    zeilen = ["import json, pathlib, sys", ""]
    if schreibe_marke:
        zeilen += [
            'marke = pathlib.Path(sys.argv[sys.argv.index("--marke") + 1])',
            "marke.parent.mkdir(parents=True, exist_ok=True)",
            'marke.write_text(json.dumps({"ok": True}), encoding="utf-8")',
            "",
        ]
    zeilen.append(f"sys.exit({code})")
    pfad.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return pfad


def _stub_auswertung(tmp_path: Path) -> Path:
    """Zaehlt seine Aufrufe in eine Datei und endet mit AUSWERTUNG_CODE."""
    pfad = tmp_path / "auswertung.py"
    pfad.write_text(
        "import os, pathlib, sys\n"
        "z = pathlib.Path(os.environ['ZAEHLER'])\n"
        "alt = z.read_text(encoding='utf-8') if z.exists() else ''\n"
        "z.write_text(alt + 'x', encoding='utf-8')\n"
        "sys.exit(int(os.environ.get('AUSWERTUNG_CODE', '0')))\n",
        encoding="utf-8",
    )
    return pfad


def _lauf(
    tmp_path: Path,
    kontrolle: Path | str,
    auswertung: Path | str,
    *,
    python: str | None = None,
    extra_env: dict[str, str] | None = None,
    argumente: tuple[str, ...] = (),
) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(
        {
            "PYTHON": python or sys.executable,
            "KONTROLLE": str(kontrolle),
            "AUSWERTUNG": str(auswertung),
            "MARKE": str(tmp_path / "ok.json"),
            "ZAEHLER": str(tmp_path / "aufrufe.txt"),
        }
    )
    env.update(extra_env or {})
    return subprocess.run(
        [BASH, str(WRAPPER), *argumente],
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


def _aufrufe(tmp_path: Path) -> str:
    zaehler = tmp_path / "aufrufe.txt"
    return zaehler.read_text(encoding="utf-8") if zaehler.exists() else ""


def test_kontrolle_ok_ruft_auswertung_genau_einmal(tmp_path: Path) -> None:
    ergebnis = _lauf(
        tmp_path, _stub_kontrolle(tmp_path, 0, True), _stub_auswertung(tmp_path)
    )
    assert ergebnis.returncode == 0
    assert _aufrufe(tmp_path) == "x"


def test_kontrolle_exit_1_blockiert_auswertung(tmp_path: Path) -> None:
    ergebnis = _lauf(
        tmp_path, _stub_kontrolle(tmp_path, 1, False), _stub_auswertung(tmp_path)
    )
    assert ergebnis.returncode == 4
    assert _aufrufe(tmp_path) == ""
    assert "ABBRUCH: Positivkontrolle Exit 1" in ergebnis.stdout


def test_kontrolle_ohne_marke_blockiert_auswertung(tmp_path: Path) -> None:
    ergebnis = _lauf(
        tmp_path, _stub_kontrolle(tmp_path, 0, False), _stub_auswertung(tmp_path)
    )
    assert ergebnis.returncode == 4
    assert _aufrufe(tmp_path) == ""


def test_nicht_ausfuehrbarer_python_blockiert_auswertung(tmp_path: Path) -> None:
    ergebnis = _lauf(
        tmp_path,
        _stub_kontrolle(tmp_path, 0, True),
        _stub_auswertung(tmp_path),
        python=str(tmp_path / "gibtsnicht" / "python"),
    )
    assert ergebnis.returncode == 4
    assert _aufrufe(tmp_path) == ""


def test_unerwarteter_fehler_blockiert_auswertung(tmp_path: Path) -> None:
    ergebnis = _lauf(
        tmp_path, _stub_kontrolle(tmp_path, 2, True), _stub_auswertung(tmp_path)
    )
    assert ergebnis.returncode == 4
    assert _aufrufe(tmp_path) == ""
    # Eine trotzdem geschriebene Marke darf nicht liegen bleiben.
    assert not (tmp_path / "ok.json").exists()


def test_auswertungsfehler_wird_durchgereicht(tmp_path: Path) -> None:
    ergebnis = _lauf(
        tmp_path,
        _stub_kontrolle(tmp_path, 0, True),
        _stub_auswertung(tmp_path),
        extra_env={"AUSWERTUNG_CODE": "3"},
    )
    assert ergebnis.returncode == 3
    assert _aufrufe(tmp_path) == "x"


def test_absichtlich_falsches_fixture_blockiert_auswertung(tmp_path: Path) -> None:
    """Echte Kontrolle mit verfaelschtem Sollwert: sie muss scheitern und blocken."""
    quelle = BENCH / "extended_benchmark" / "yun_full" / "positivkontrolle_p5.py"
    text = quelle.read_text(encoding="utf-8").replace('"wertgleich": 5,', '"wertgleich": 6,')
    assert '"wertgleich": 6,' in text, "Sollwert im Fixture nicht gefunden"

    kopie = tmp_path / "kontrolle_kaputt.py"
    kopie.write_text(text, encoding="utf-8")

    # PYTHONPATH, damit die Kopie `extended_benchmark` findet, obwohl sie nicht im
    # Repo liegt; sonst scheiterte sie am Import statt am Sollwert.
    # `extended_benchmark` liegt unter public_benchmark, nicht im Repo-Root.
    ergebnis = _lauf(
        tmp_path, kopie, _stub_auswertung(tmp_path), extra_env={"PYTHONPATH": str(BENCH)}
    )

    assert ergebnis.returncode == 4
    assert _aufrufe(tmp_path) == ""
    assert "wertgleich" in ergebnis.stdout


def test_wrapper_nutzt_die_echte_kontrolle(tmp_path: Path) -> None:
    """Mit der echten Kontrolle laeuft es bis zur Auswertung, hier ohne Lauf.

    `--neu` zeigt bewusst auf einen Pfad ohne Predictions: der Exit 2 haengt so
    am fehlenden Lauf und nicht am Zustand des echten Laufverzeichnisses. Seit
    der P5-Lauf 67 verwertbare Records hat, existiert
    `runs/yun699_p5_24000_20261118/predictions.jsonl`; ohne diesen Pfad
    schriebe die echte Auswertung ihre Berichte nach `iterativ/ergebnisse/`.
    Ein Test darf den echten Stand nicht ueberschreiben.
    """
    ohne_lauf = tmp_path / "kein_lauf" / "predictions.jsonl"
    ergebnis = _lauf(
        tmp_path,
        BENCH / "extended_benchmark" / "yun_full" / "positivkontrolle_p5.py",
        BENCH / "extended_benchmark" / "yun_full" / "werte_p5_aus.py",
        argumente=("--neu", str(ohne_lauf)),
    )
    assert ergebnis.returncode == 2
    assert "Lauf liegt noch nicht vor" in ergebnis.stdout
    assert not (tmp_path / "kein_lauf").exists()
