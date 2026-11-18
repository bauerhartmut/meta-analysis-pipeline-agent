#!/usr/bin/env python
"""Pruefregeln fuer eine extrahierte Zelle (Variante D).

Die Regeln sind bewusst eng: Sie sollen eine Zelle nur dann verwerfen, wenn sie
in sich widerspruechlich ist. Alles Weiche bleibt eine Warnung, damit
untypische, aber korrekte Studienwerte nicht verloren gehen.

Geprueft werden die sechs Punkte aus dem Auftrag:

* Ereignisse gegen Gruppengroessen (events <= N, ganzzahlig),
* Mittelwerte und Standardabweichungen (SD > 0, SD nicht absurd zum Mittelwert),
* Prozentangaben gegen absolute Haeufigkeiten (Wert < 1 bei N > 1),
* Armzuordnung (Extremverhaeltnis der Gruppengroessen, Arm im Zitat),
* Outcome-Zuordnung (events nur binaer, mean/SD nur kontinuierlich),
* Zeitpunktkonsistenz (alle neuen Zellen einer Antwort tragen denselben Zeitpunkt).
"""

from __future__ import annotations

from typing import Any


# Regeln, die in der Messung gegen den GLM-Lauf ausschliesslich falsche Zellen
# markiert haben (oder fast nur). Nur diese duerfen eine Zelle verwerfen.
HARTE_REGELN = {
    "ereignisse_ueber_gruppengroesse",
    "ereignis_nicht_ganzzahlig",
    "negatives_ereignis",
    "prozent_statt_anzahl",
    "sd_nicht_positiv",
    "gruppengroesse_nicht_positiv",
    "ereignisse_bei_kontinuierlichem_outcome",
    "mittelwert_bei_binaerem_outcome",
}


def _wert(zellen: dict[str, float], feld: str) -> float | None:
    return zellen.get(feld)


def pruefe_zelle(record: dict, feld: str, wert: float, zellen: dict[str, float], zitat: str = "") -> list[str]:
    """Liefert Verstossnamen fuer eine einzelne Zelle (leer = unbeanstandet)."""
    typ = (record.get("context") or {}).get("outcome_type") or ""
    arm = "intervention" if feld.startswith("intervention") else "comparator"
    anderer = "comparator" if arm == "intervention" else "intervention"
    verstoesse: list[str] = []
    n = _wert(zellen, f"{arm}_group_size")
    n_anderer = _wert(zellen, f"{anderer}_group_size")

    if feld.endswith("_events"):
        if typ and typ != "binary":
            verstoesse.append("ereignisse_bei_kontinuierlichem_outcome")
        if wert is not None:
            if wert < 0:
                verstoesse.append("negatives_ereignis")
            elif abs(wert - round(wert)) > 1e-9:
                verstoesse.append("ereignis_nicht_ganzzahlig")
            if n and wert > n:
                verstoesse.append("ereignisse_ueber_gruppengroesse")
            if n and n > 1 and 0 < wert < 1:
                verstoesse.append("prozent_statt_anzahl")

    if feld.endswith("_mean") or feld.endswith("_standard_deviation"):
        if typ and typ != "continuous":
            verstoesse.append("mittelwert_bei_binaerem_outcome")
    if feld.endswith("_mean") and wert is not None and n and n > 1 and 0 < abs(wert) < 1:
        verstoesse.append("anteil_statt_mittelwert")

    if feld.endswith("_standard_deviation"):
        if wert is not None and wert <= 0:
            verstoesse.append("sd_nicht_positiv")
        mittel = _wert(zellen, f"{arm}_mean")
        if wert is not None and mittel and abs(mittel) > 0 and wert > 5 * abs(mittel):
            verstoesse.append("sd_gegen_mittelwert")

    if feld.endswith("_group_size") and wert is not None and wert <= 0:
        verstoesse.append("gruppengroesse_nicht_positiv")

    if feld.endswith("_group_size") and wert is not None and n_anderer and wert > 0 and n_anderer > 0:
        verhaeltnis = max(wert, n_anderer) / min(wert, n_anderer)
        if verhaeltnis > 3:
            verstoesse.append("arme_sehr_ungleich")

    if zitat and feld.startswith("comparator") and feld.endswith(("_events", "_mean")):
        if (record.get("context") or {}).get("intervention"):
            name = str(record["context"]["intervention"]).lower()
            if name and name in zitat.lower() and str(record["context"].get("comparator") or "").lower() not in zitat.lower():
                verstoesse.append("armbezug_nur_intervention_im_zitat")
    return verstoesse


def pruefe_zeitpunkt(zellen_neu: list[dict]) -> list[str]:
    """Alle neu hinzugefuegten Zellen muessen denselben Zeitpunkt tragen."""
    labels = {str(z.get("timepoint") or "").strip().lower() for z in zellen_neu}
    labels = {l for l in labels if l}
    if len(labels) > 1:
        return ["zeitpunkte_gemischt"]
    return []


def filtere(
    record: dict,
    kandidaten: dict[str, dict[str, Any]],
    nur_harte: bool = True,
    basis: dict[str, float] | None = None,
) -> tuple[dict[str, dict], list[dict]]:
    """Prueft Kandidatenzellen und verwirft nur die mit hartem Verstoss.

    `kandidaten` bildet Feld -> {wert, zitat, ...}. `basis` sind die bereits
    vorhandenen Zellen des Records; sie gehen in die Pruefung ein, damit eine
    neue Ereigniszahl gegen die vorhandene Gruppengroesse geprueft wird und
    nicht gegen eine leere Menge. Rueckgabe: akzeptierte Zellen und Liste der
    Verwerfungen mit Begruendung.
    """
    werte: dict[str, float] = dict(basis or {})
    werte.update({feld: eintrag["wert"] for feld, eintrag in kandidaten.items() if eintrag.get("wert") is not None})
    akzeptiert: dict[str, dict] = {}
    verworfen: list[dict] = []
    for feld, eintrag in kandidaten.items():
        if eintrag.get("wert") is None:
            continue
        verstoesse = pruefe_zelle(record, feld, eintrag["wert"], werte, eintrag.get("zitat") or "")
        if nur_harte:
            verstoesse = [v for v in verstoesse if v in HARTE_REGELN]
        if verstoesse:
            verworfen.append({"feld": feld, "wert": eintrag["wert"], "gruende": verstoesse})
        else:
            akzeptiert[feld] = eintrag
    return akzeptiert, verworfen
