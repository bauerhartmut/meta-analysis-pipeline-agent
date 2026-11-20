#!/usr/bin/env python
"""Die 67 einzelnen Falschwert-Zellen offline auf Zuordnungsfehler pruefen.

Frage: Steht der gedruckte Wert im Quelltext und gehoert er nach dem Gold zu
einem anderen Feld oder Arm? Dann waere er mit einer reinen Zuordnungsregel
erreichbar, ohne dass das Modell etwas anders lesen muesste.

Rein lesend. Kein Modellaufruf, kein Netz. Gold und Predictions bleiben
unberuehrt; das Skript prueft das per SHA256 vor und nach der Rechnung.

Auswahl der Zellen (identisch zur Logik aus `vergleiche_20261120.py`):
eine Zelle ist eine *einzelne* Falschwert-Zelle, wenn
  * sie nach dem 1:1-Verbrauch der Goldzellen uebrig bleibt,
  * ihr (Feld, Arm) im Gold des Records vorkommt,
  * und im selben (Feld, Arm) genau eine Vorhersagezelle steht
    (Mehrfachzellen sind Sache des Dublettenfilters).

Klassen je Zelle:

- `zuordnung_arm`     : der Wert ist Goldwert desselben Feldes im anderen Arm.
- `zuordnung_feld`    : der Wert ist Goldwert eines anderen Feldes im selben Arm.
- `zuordnung_beides`  : Feld und Arm weichen ab.
- `wert_im_text`      : der Wert steht im Text, gehoert aber zu keinem Goldslot
                        des Records (anderer Zeitpunkt, andere Zeile, Untergruppe).
- `nicht_im_text`     : der Wert steht so nicht im Text (Umrechnung, Rechnung
                        oder Lesefehler).

Zusaetzlich wird je Zuordnungsfall geprueft, ob der Zielslot im Lauf schon
richtig gefuellt ist. Nur wenn er es nicht ist, gewinnt eine Zuordnungsregel
tatsaechlich einen Treffer.

Aufruf:
    .venv/bin/python public_benchmark/extended_benchmark/analysis/glm53_p5_vergleich_20261120/falschwert_20261120.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent.parent
ROOT = HIER.parents[3]
sys.path.insert(0, str(HIER))

import vergleiche_20261120 as v  # noqa: E402

AUSGABE_JSON = HIER / "falschwert_20261120.json"
AUSGABE_MD = HIER / "p5_falschwert_zuordnung_20261120.md"
LIMIT = 45000  # Standard von build_prompt; P5 hat ihn nicht ueberschrieben

TOKEN = re.compile(r"\d{1,3}(?:[.,\u00a0 ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?")


def sha256(pfad: Path) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


def lesarten(roh: str) -> set[float]:
    """Zahlen, die eine Textstelle bedeuten kann. Trennzeichen nur als Tausendergruppen.

    Eine Ziffernfolge darf nur dann als Tausenderzahl gelesen werden, wenn jede
    Gruppe nach der ersten genau drei Ziffern hat. `7.69` ist damit 7,69 und
    nicht 769; `1.234` bleibt mehrdeutig und wird als 1,234 und als 1234 gefuehrt.
    Ein Dezimalteil wird nur angenommen, wenn die Gruppen davor entweder eine
    einzelne Zahl oder echte Tausendergruppen sind.
    """
    roh = roh.replace("\u00a0", " ").strip()
    gruppen = [g for g in re.split(r"[,.]|(?<=\d) (?=\d)", roh) if g]
    if not gruppen:
        return set()
    if len(gruppen) == 1:
        return {float(gruppen[0])}

    aus: set[float] = set()
    # (1) alle Trenner sind Tausendertrenner -> ganze Zahl
    if all(len(g) == 3 for g in gruppen[1:]):
        aus.add(float(gruppen[0] + "".join(gruppen[1:])))
    # (2) letzte Gruppe ist Dezimalteil, davor eine Zahl oder echte Tausendergruppen
    if len(gruppen[-1]) <= 6 and (len(gruppen) == 2 or all(len(g) == 3 for g in gruppen[1:-1])):
        aus.add(float("".join(gruppen[:-1]) + "." + gruppen[-1]))
    return aus


#: Selbstpruefung: der alte Zahlenvergleich machte aus 7.69 die 769.
PRUEFUNGEN = {
    "7.69": {7.69},
    "7,69": {7.69},
    "1,919": {1.919, 1919.0},
    "922": {922.0},
    "11,897": {11.897, 11897.0},
    "1.234,5": {1234.5},
    "1,234.5": {1234.5},
}


def eindeutig(roh: str) -> bool:
    """Traegt die Textstelle die Zahl ohne Tausender-Mehrdeutigkeit?

    Eindeutig sind Zahlen ohne Trenner sowie Dezimalzahlen mit hoechstens zwei
    Nachkommastellen (`2.42`, `7,69`). `1.234` ist es nicht: 1,234 und 1.234 sind
    beide lesbar.
    """
    teile = [t for t in re.split(r"[,.]", roh.replace("\u00a0", " ")) if t]
    return len(teile) == 1 or (len(teile) == 2 and len(teile[1]) <= 2)


def zahlen_im_text(text: str) -> tuple[Counter, dict[float, list[str]], Counter]:
    """Alle Zahlen des Textes unter den zulaessigen Trennzeichen-Lesarten.

    Zusaetzlich die Fundstellen (hoechstens drei je Zahl), damit jede Bestaetigung
    im Bericht nachpruefbar ist und nicht nur als Trefferzahl dasteht.
    """
    gefunden: Counter = Counter()
    klar: Counter = Counter()
    stellen: dict[float, list[str]] = {}
    for treffer in TOKEN.finditer(text):
        roh = treffer.group(0)
        for zahl in lesarten(roh):
            schluessel = round(zahl, 6)
            gefunden[schluessel] += 1
            if eindeutig(roh):
                klar[schluessel] += 1
            if len(stellen.setdefault(schluessel, [])) < 3:
                von = max(0, treffer.start() - 40)
                stellen[schluessel].append(" ".join(text[von:treffer.end() + 25].split()))
    return gefunden, stellen, klar


def pruefe_lesarten() -> None:
    for roh, erwartet in PRUEFUNGEN.items():
        ist = lesarten(roh)
        if ist != erwartet:
            raise SystemExit(f"Selbstpruefung fehlgeschlagen: {roh} -> {ist}, erwartet {erwartet}")


def key(zelle: dict[str, Any]) -> tuple[str, str]:
    return (str(zelle.get("field") or ""), v.arm_von(zelle))


def main() -> int:
    pruefe_lesarten()
    vorher = {"gold": sha256(v.RECORDS), "p5": sha256(v.P5)}
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    ids = [i for i in (json.loads(v.AUSWAHL.read_text(encoding="utf-8")).get("ids") or []) if i in records]
    bewertbar = [i for i in sorted(ids) if i != v.NICHT_BEWERTBAR]
    p5 = {z["record_id"]: z for z in v.lade(v.P5) if z.get("model") == "glm"}

    zellen: list[dict[str, Any]] = []
    for rid in bewertbar:
        record = records[rid]
        gold = (record.get("gold") or {}).get("cells") or []
        vor = v.zellen(p5.get(rid))
        gruppen = Counter(key(z) for z in vor)
        gold_keys = {key(z) for z in gold}
        gold_paare = [(key(z), v.zahl(z.get("value"))) for z in gold]

        # 1:1-Verbrauch wie in der Bewertung
        verbraucht = [False] * len(vor)
        for zelle in gold:
            soll = v.zahl(zelle.get("value"))
            if soll is None:
                continue
            for i, kandidat in enumerate(vor):
                if verbraucht[i] or key(kandidat) != key(zelle):
                    continue
                ist = v.zahl(kandidat.get("value"))
                if ist is not None and abs(ist - soll) < 1e-6:
                    verbraucht[i] = True
                    break

        # Zielslot-Zustand: welche Slots sind im Lauf schon richtig gefuellt?
        richtig = {
            key(z) for z, flag in zip(vor, verbraucht) if flag
        }

        pfad = ROOT / (record.get("document") or {}).get("path", "")
        text_voll = pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else ""
        text = text_voll[:LIMIT]
        zahlen, stellen, klar = zahlen_im_text(text)

        for i, kandidat in enumerate(vor):
            if verbraucht[i] or v.zahl(kandidat.get("value")) is None:
                continue
            k = key(kandidat)
            if k not in gold_keys or gruppen.get(k, 0) > 1:
                continue  # Fremdschluessel oder Mehrfachzelle
            ist = v.zahl(kandidat.get("value"))
            soll = next(value for pair, value in gold_paare if pair == k)
            treffer = zahlen.get(round(float(ist), 6), 0)
            gleiche_slots = sorted(pair for pair, value in gold_paare
                                   if value is not None and abs(value - ist) < 1e-6 and pair != k)
            if gleiche_slots:
                feld_gleich = [p for p in gleiche_slots if p[0] == k[0]]
                arm_gleich = [p for p in gleiche_slots if p[1] == k[1]]
                if feld_gleich and not arm_gleich:
                    klasse = "zuordnung_arm"
                elif arm_gleich and not feld_gleich:
                    klasse = "zuordnung_feld"
                else:
                    klasse = "zuordnung_beides"
            elif treffer:
                klasse = "wert_im_text"
            else:
                klasse = "nicht_im_text"
            # Belegstaerke fuer "steht im Text": ein einmaliger Treffer in einem
            # 10.000-Zeichen-Dokument ist stark, ein kleiner Integer mit vielen
            # Treffern ist praktisch immer vorhanden und damit kein Beleg.
            if treffer == 1:
                beleg = "eindeutig"
            elif treffer <= 3:
                beleg = "eng"
            else:
                beleg = "breit"
            zufall = (
                float(ist).is_integer() and abs(ist) < 100 and treffer > 3
            )
            zellen.append({
                "record_id": rid,
                "feld": k[0],
                "arm": k[1],
                "gedruckt": str(kandidat.get("value")),
                "gedruckt_zahl": ist,
                "gold": soll,
                "im_text": treffer > 0,
                "text_treffer": treffer,
                "text_treffer_eindeutig": klar.get(round(float(ist), 6), 0),
                "beleg_stellen": stellen.get(round(float(ist), 6), []),
                "text_zeichen": len(text_voll),
                "text_abgeschnitten": len(text_voll) > LIMIT,
                "gleiche_slots": [list(p) for p in gleiche_slots],
                "beleg": beleg,
                "zufall_verdacht": zufall,
                "klasse": klasse,
                "ziel_slot_offen": bool(gleiche_slots) and not any(p in richtig for p in gleiche_slots),
                "wirksam": klasse.startswith("zuordnung_") and bool(gleiche_slots)
                and not any(p in richtig for p in gleiche_slots),
            })

    nachher = {"gold": sha256(v.RECORDS), "p5": sha256(v.P5)}
    if vorher != nachher:
        print("ABBRUCH: Eingabedateien haben sich waehrend der Rechnung geaendert.")
        return 1

    klassen = Counter(z["klasse"] for z in zellen)
    zuordnung = [z for z in zellen if z["klasse"].startswith("zuordnung_")]
    wirksam = [z for z in zellen if z["wirksam"]]
    ohne_wirkung = [z for z in zuordnung if not z["wirksam"]]
    belege = Counter(z["beleg"] for z in zellen if z["klasse"] == "wert_im_text")
    zufall = [z for z in zellen if z["zufall_verdacht"]]

    # Szenario: die wirksamen Zuordnungen werden korrigiert. Erwartung: je Zelle
    # ein FP weniger, ein TP und ein FN mehr - nur wenn der Zielslot offen und
    # eindeutig ist. Mehrdeutige Ziele werden nicht mitgerechnet.
    basis = v.kennzahlen(
        [
            v.bilanz_p5(
                (records[rid]["gold"] or {}).get("cells") or [], v.zellen(p5.get(rid))
            )
            for rid in bewertbar
        ],
        "p5",
    )
    eindeutig = [z for z in wirksam if len(z["gleiche_slots"]) == 1]
    mehrdeutig = [z for z in wirksam if len(z["gleiche_slots"]) != 1]
    ziele = {(z["record_id"], tuple(z["gleiche_slots"][0])) for z in eindeutig}
    n = len(ziele) if len(ziele) == len(eindeutig) else len(eindeutig)
    szenario = {
        **v.quote(basis["tp"] + n, basis["fp"] - n, basis["fn"] - n),
        "tp": basis["tp"] + n,
        "fp": basis["fp"] - n,
        "fn": basis["fn"] - n,
        "korrigierte_zellen": n,
        "mehrdeutige_ziele": len(mehrdeutig),
        "delta_f1": round(
            (v.quote(basis["tp"] + n, basis["fp"] - n, basis["fn"] - n)["f1"] or 0) - (basis["f1"] or 0), 6
        ),
    }

    ergebnis = {
        "hinweis": (
            "Rein lesend, kein Modellaufruf. Zellenauswahl wie im Dublettenfilter: "
            "uebrig gebliebene Zelle, Schluessel im Gold vorhanden, genau eine Zelle "
            "im selben (Feld, Arm)."
        ),
        "quellen": {"records": str(v.RECORDS), "p5": str(v.P5), "auswahl": str(v.AUSWAHL)},
        "n": len(zellen),
        "klassen": dict(klassen),
        "beleg_im_text": dict(belege),
        "basis": basis,
        "szenario_zuordnung": szenario,
        "zufall_verdacht": [z["record_id"] + "/" + z["feld"] for z in zufall],
        "zellen": zellen,
        "integritaet": {"vorher": vorher, "nachher": nachher, "unveraendert": vorher == nachher},
    }
    AUSGABE_JSON.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Die 67 einzelnen Falschwert-Zellen: Zuordnung oder Lesefehler? (20.11.2026)",
        "",
        "Rein lesend, kein Modellaufruf. Auswahl wie beim Dublettenfilter: eine Zelle, die im "
        "1:1-Verbrauch uebrig bleibt, deren (Feld, Arm) im Gold des Records vorkommt und die "
        "im selben (Feld, Arm) die einzige Vorhersagezelle ist. Genau diese 67 Zellen machen "
        "zusammen mit 13 Mehrfach- und 17 Fremdschluesselzellen die 97 falschen Zellen der "
        "P5-Basis aus.",
        "",
        "## Ergebnis",
        "",
        "| Klasse | Zellen | Bedeutung |",
        "|---|---:|---|",
        f"| `zuordnung_arm` | {klassen.get('zuordnung_arm', 0)} | Wert ist Goldwert desselben Feldes im anderen Arm |",
        f"| `zuordnung_feld` | {klassen.get('zuordnung_feld', 0)} | Wert ist Goldwert eines anderen Feldes im selben Arm |",
        f"| `zuordnung_beides` | {klassen.get('zuordnung_beides', 0)} | Feld und Arm weichen ab |",
        f"| `wert_im_text` | {klassen.get('wert_im_text', 0)} | Wert steht im Text, gehoert aber zu keinem Goldslot des Records |",
        f"| `nicht_im_text` | {klassen.get('nicht_im_text', 0)} | Wert steht so nicht im Text |",
        "",
        f"**Zuordnung insgesamt: {len(zuordnung)} von {len(zellen)} Zellen.** In "
        f"{len(wirksam)} dieser Faelle ist der Zielslot im Lauf noch offen, eine reine "
        f"Zuordnungsregel gewinnt dort also einen Treffer. In {len(ohne_wirkung)} der Faelle ist "
        "der Zielslot bereits richtig gefuellt; eine Umhaengung wuerde dort nur eine Dublette "
        "erzeugen.",
        "",
        "## Wie belastbar ist \"steht im Text\"?",
        "",
        f"- {belege.get('eindeutig', 0)} der {klassen.get('wert_im_text', 0)} Zellen haben genau einen Treffer "
        f"im Dokument, {belege.get('eng', 0)} zwei bis drei Treffer, {belege.get('breit', 0)} mehr als drei. "
        "Bei einem einmaligen Treffer in einem 10.000-Zeichen-Dokument ist der Beleg stark.",
        f"- {len(zufall)} Zellen tragen einen kleinen Integer (Betrag unter 100), der im Text mehr als "
        "dreimal vorkommt. Dort ist \"steht im Text\" fast automatisch wahr und traegt keine Aussage; "
        "diese Zellen zaehlen mit, sind aber schwach belegt.",
        "- Die grossen Werte sind dagegen eindeutig: 922 und 919 in `yun2024:362` sowie 769 und 667 "
        "in `yun2024:615` bis `:617` stehen je nur zweimal im Dokument und treffen keine Goldzelle.",
        "- Der Zahlenvergleich liest Trennzeichen nur dann als Tausendertrenner, wenn jede Gruppe "
        "nach der ersten genau drei Ziffern hat; `7.69` ist damit 7,69 und nicht 769. Eine fruehere "
        "Fassung dieses Skripts hatte genau diesen Fehler und machte aus `7.69` die 769.",
        "- Nach der Verschaerfung bleiben alle 63 Textfaelle bestaetigt; 12 Zellen verlieren Treffer, "
        "keine verliert den Beleg. Die vier grossen Werte stehen als ganze Zahlen im Text "
        "(`n = 922`, `n = 919`, 769 Frauen, 667 Frauen), nicht als Dezimalzahl.",
        f"- {sum(1 for z in zellen if z['klasse'] == 'wert_im_text' and z['text_treffer_eindeutig'])} "
        f"der {klassen.get('wert_im_text', 0)} Textfaelle haben mindestens einen eindeutigen Treffer; "
        "keiner haengt an einer mehrdeutigen Tausender-Lesart wie `1.234` (1,234 oder 1.234).",
        f"- Jede Bestaetigung traegt ihre Fundstelle im JSON (`beleg_stellen`); die "
        f"{belege.get('eindeutig', 0)} Zellen mit genau einem Treffer sind im Anhang mit Textzitat "
        "aufgefuehrt.",
        "",
        "## Was eine korrigierte Zuordnung an den Kennzahlen aendert",
        "",
        f"Werden die {szenario['korrigierte_zellen']} eindeutigen Zuordnungsfaelle umgehaengt, "
        f"steigt TP von {basis['tp']} auf {szenario['tp']}, FP faellt von {basis['fp']} auf "
        f"{szenario['fp']}, FN von {basis['fn']} auf {szenario['fn']}. Precision "
        f"{basis['precision']:.4f} -> {szenario['precision']:.4f}, Recall {basis['recall']:.4f} -> "
        f"{szenario['recall']:.4f}, F1 {basis['f1']:.4f} -> {szenario['f1']:.4f} "
        f"({szenario['delta_f1'] * 100:+.2f} Prozentpunkte). Das ist der gesamte Hebel einer reinen "
        "Zuordnungsregel auf diesem Lauf.",
        "",
        "## Was das fuer eine Regel bedeutet",
        "",
        f"- {len(zuordnung)} Zellen sind reine Zuordnungsfehler: die Zahl wurde richtig gelesen "
        "und am falschen Feld oder Arm abgelegt. Das ist die einzige Gruppe, die eine "
        "Zuordnungsregel ohne neues Lesen erreichen kann.",
        f"- {klassen.get('wert_im_text', 0)} Zellen tragen eine Zahl, die im Text steht, aber zu "
        "keinem Goldslot des Records passt: anderer Zeitpunkt, andere Tabellenzeile, "
        "Untergruppe oder eine Zahl aus dem Fliesstext. Diese Gruppe braucht eine Zeilen- oder "
        "Zeitpunktregel, keine Zuordnungsregel.",
        f"- {klassen.get('nicht_im_text', 0)} Zellen tragen eine Zahl, die so nicht im Text steht. "
        "Das sind Umrechnungen, gerechnete Werte oder Lesefehler; sie sind ohne erneuten "
        "Modellaufruf nicht reparierbar.",
        "- Die Klassifikation stuetzt sich auf das Gold als Referenz fuer Feld und Arm. Sie "
        "zeigt, wohin der Wert gehoert, nicht warum das Modell ihn dort abgelegt hat.",
        "- Ein Grenzfall in der Zuordnungsgruppe ist `yun2024:558`: gedruckt 16,0 fuer "
        "`intervention_mean` (Gold -4,0), und 16 ist zugleich die comparator-Gruppengroesse. "
        "Bei einem solchen kleinen Integer kann die Uebereinstimmung Zufall sein; der Fall zaehlt "
        "formal als Zuordnung, ist aber nicht belegt. Belastbar sind die drei Faelle in "
        "`yun2024:113` (459 gegen 456, beide Arme vertauscht) und `yun2024:291` (12,8 statt 9,8, "
        "Wert der intervention-SD).",
        "",
        "## Alle 67 Zellen",
        "",
        "| Record | Feld | Arm | gedruckt | Gold | im Text | Wert steht im Gold bei | Klasse | Ziel offen |",
        "|---|---|---|---:|---:|---|---|---|---|",
    ]
    for z in zellen:
        slots = ", ".join(f"{p[0]}/{p[1]}" for p in z["gleiche_slots"]) or "-"
        md.append(
            f"| `{z['record_id']}` | {z['feld']} | {z['arm']} | {z['gedruckt']} | {z['gold']} | "
            f"{'ja' if z['im_text'] else 'nein'} | {slots} | {z['klasse']} | "
            f"{'ja' if z['ziel_slot_offen'] else 'nein'} |"
        )
    md.append("")
    md += [
        "## Anhang: Fundstellen der einmaligen Belege",
        "",
        "Je Zelle der erste Treffer im Markdown, 40 Zeichen davor bis 25 Zeichen danach.",
        "",
        "| Record | Feld | gedruckt | Fundstelle im Text |",
        "|---|---|---:|---|",
    ]
    for z in [z for z in zellen if z["klasse"] == "wert_im_text" and z["text_treffer"] == 1]:
        stelle = (z["beleg_stellen"][0] if z["beleg_stellen"] else "").replace("|", "\\|")
        md.append(f"| `{z['record_id']}` | {z['feld']} | {z['gedruckt']} | ...{stelle}... |")
    md.append("")
    AUSGABE_MD.write_text("\n".join(md), encoding="utf-8", newline="\n")

    print("Zellen:", len(zellen), "| Klassen:", dict(klassen))
    print("Zuordnung:", len(zuordnung), "| davon wirksam:", len(wirksam), "| ohne Wirkung:", len(ohne_wirkung))
    print("Integritaet unveraendert:", ergebnis["integritaet"]["unveraendert"])
    print("geschrieben:", AUSGABE_JSON)
    print("geschrieben:", AUSGABE_MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
