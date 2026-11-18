"""Job-Journal und Doppelstart-Sperre fuer einen Lauf — nur unter `retry-strategie neu`.

Zwei kleine Dateien im Laufverzeichnis, keine Datenbank:

* `jobs.jsonl` (append-only, jede Zeile mit `fsync`) haelt fest, welcher Auftrag
  lief und wie er endete. Nach einem Absturz zeigt der Replay, welche Auftraege
  unterbrochen wurden. Wahrheit ueber ein vorhandenes Ergebnis bleibt die Zeile
  in `predictions.jsonl`; das Journal erklaert nur, was dazwischen passiert ist.
* `harness.lock` verhindert den Doppelstart, der am 17.11. Duplikate erzeugt hat.

Bewusst ohne PID-Lebendpruefung: `os.kill(pid, 0)` beendet unter Windows den
Prozess, statt ihn zu testen. Die Sperre gilt deshalb nach Alter, wie die
90-Minuten-Regel in `nachzug_ausfaelle.sh`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

#: Reihenfolge der Zustaende eines Auftrags im Journal.
STATUS = ("running", "completed", "failed")

#: Ab wann eine vorgefundene Sperre als verwaist gilt.
MAX_ALTER_MIN = 90


def _jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class JobJournal:
    """Append-only Protokoll je (record_id, model)."""

    pfad: Path

    def schreibe(
        self, record_id: str, model: str, status: str, *, fehlerklasse: str = ""
    ) -> dict:
        """Haengt eine Zeile an und synct sie auf die Platte."""
        if status not in STATUS:
            raise ValueError(f"unbekannter Status: {status}")
        zeile = {
            "ts": _jetzt(),
            "record_id": record_id,
            "model": model,
            "status": status,
            "fehlerklasse": fehlerklasse,
        }
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        with self.pfad.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(zeile, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return zeile

    def unterbrochene(self) -> list[dict]:
        """Auftraege mit `running`, fuer die kein Abschluss im Journal steht."""
        if not self.pfad.exists():
            return []
        offen: dict[tuple[str, str], dict] = {}
        for zeile in self.pfad.read_text(encoding="utf-8").splitlines():
            if not zeile.strip():
                continue
            try:
                eintrag = json.loads(zeile)
            except json.JSONDecodeError:
                continue  # halb geschriebene Zeile nach Absturz
            schluessel = (eintrag.get("record_id"), eintrag.get("model"))
            if eintrag.get("status") == "running":
                offen[schluessel] = eintrag
            else:
                offen.pop(schluessel, None)
        return sorted(offen.values(), key=lambda e: (e["record_id"], e["model"]))


class SperreBelegt(RuntimeError):
    """Ein anderer Prozess haelt die Sperre."""


@dataclass
class RunSperre:
    """Doppelstart-Schutz je Laufverzeichnis."""

    pfad: Path
    max_alter_min: int = MAX_ALTER_MIN

    def nehmen(self) -> bool:
        """Nimmt die Sperre; `False` heisst, eine abgelaufene wurde uebernommen."""
        inhalt = json.dumps({"pid": os.getpid(), "ts": _jetzt()}) + "\n"
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        try:
            griff = os.open(self.pfad, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if not self._abgelaufen():
                raise SperreBelegt(f"gehalten von PID {self.pid()}") from None
            self.pfad.write_text(inhalt, encoding="utf-8")
            return False
        with os.fdopen(griff, "w", encoding="utf-8") as handle:
            handle.write(inhalt)
        return True

    def freigeben(self) -> bool:
        """Loescht die Sperre, aber nur die eigene."""
        if self.pid() != str(os.getpid()):
            return False
        self.pfad.unlink(missing_ok=True)
        return True

    def pid(self) -> str:
        try:
            return str(json.loads(self.pfad.read_text(encoding="utf-8")).get("pid"))
        except (OSError, json.JSONDecodeError):
            return "unbekannt"

    def _abgelaufen(self) -> bool:
        if not self.pfad.exists():
            return True
        alter_s = datetime.now(timezone.utc).timestamp() - self.pfad.stat().st_mtime
        return alter_s > self.max_alter_min * 60
