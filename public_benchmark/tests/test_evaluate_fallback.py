"""Tests fuer Versionsetikett und Zellklassen der Rueckfall-Auswertung."""

from __future__ import annotations

import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark import run_extended_extraction as runner  # noqa: E402
from extended_benchmark.evaluate_fallback import klassifiziere  # noqa: E402


def test_normalisierung_ergaenzt_einheit_nur_mit_beleg() -> None:
    from extended_benchmark.evaluate_fallback import normalisiere_label

    # Einheit kommt aus dem annotierten Ziel, nicht aus der Zahl.
    assert normalisiere_label("24", "week 24") == ("week 24", "ok")
    assert normalisiere_label("6", "month 6") == ("month 6", "ok")
    assert normalisiere_label("1", "day 1") == ("day 1", "ok")
    # Ohne passendes Ziel bleibt die Zahl unklar.
    assert normalisiere_label("24", "month 6") == ("", "unklar")
    assert normalisiere_label("24", "") == ("", "unklar")


def test_null_wird_nur_bei_belegter_baseline_zu_baseline() -> None:
    from extended_benchmark.evaluate_fallback import normalisiere_label

    assert normalisiere_label("0", "baseline") == ("baseline", "ok")
    assert normalisiere_label("0", "week 24") == ("", "unklar")


def test_bereits_korrekte_labels_bleiben_unveraendert() -> None:
    from extended_benchmark.evaluate_fallback import normalisiere_label

    assert normalisiere_label("week 24", "week 24") == ("week 24", "ok")
    assert normalisiere_label("baseline", "week 24") == ("baseline", "ok")
    assert normalisiere_label("Post-test", "week 24") == ("post-test", "ok")
    assert normalisiere_label("", "week 24") == ("", "leer")


def test_arme_behalten_ihre_zeitpunkte() -> None:
    from extended_benchmark.evaluate_fallback import arme_gemischt

    gleich = [{"arm": "intervention", "timepoint": "24"}, {"arm": "comparator", "timepoint": "24"}]
    assert arme_gemischt(gleich, "week 24") is False
    # Genau der Fall yun2024:75: Intervention Woche 24, Komparator Baseline.
    gemischt = [{"arm": "intervention", "timepoint": "24"}, {"arm": "comparator", "timepoint": "0"}]
    assert arme_gemischt(gemischt, "week 24") is True
    # Fehlt der Zeitpunkt eines Arms, wird nichts uebertragen.
    assert arme_gemischt([{"arm": "intervention", "timepoint": "24"}], "week 24") is False
    assert (
        arme_gemischt(
            [{"arm": "intervention", "timepoint": "24"}, {"arm": "comparator", "timepoint": ""}],
            "week 24",
        )
        is False
    )


def test_kaputtes_json_wird_wiederholt() -> None:
    """Strukturell unlesbares JSON gilt als Ausfall, eine leere Zellenliste nicht."""
    assert runner.json_kaputt("kein_json")
    assert runner.json_kaputt("kein_objet")
    assert runner.json_kaputt("json_fehler: Expecting ',' delimiter")
    assert not runner.json_kaputt("")
    assert not runner.json_kaputt("keine_zellen")
    assert not runner.json_kaputt("keine_verwertbaren_zellen")


def test_lauf_ohne_annotation_heisst_nicht_v6() -> None:
    ohne = runner.bestimme_version(fallback=True, target="")
    assert ohne == runner.PROMPT_VERSION == "v2_timepoint"
    mit = runner.bestimme_version(fallback=True, target="Post-test")
    assert mit == "v6_target_fallback"


def test_cache_suffix_und_vorrang_der_flags() -> None:
    assert runner.bestimme_version(fallback=True, target="Post-test", cache_buster=True) == "v6_target_fallback_cb"
    assert runner.bestimme_version(absolute_counts=True, target="Post-test") == "v3_abs_count"
    assert runner.bestimme_version(last_timepoint=True, target="Post-test") == "v4_last_timepoint"
    assert runner.bestimme_version(target_timepoint=True, target="") == "v2_timepoint"
    assert runner.bestimme_version(target_timepoint=True, target="Post-test") == "v5_target_timepoint"


def test_belegstufe_bevorzugt_gedruckte_und_artikelbelege() -> None:
    from extended_benchmark.evaluate_fallback import belegstufe

    assert belegstufe("Week 24", "", "") == ("week 24", "gedruckt")
    assert belegstufe("12 months", "", "") == ("month 12", "gedruckt")
    assert belegstufe("24", "week 24", "assessed at 24 weeks of treatment") == ("week 24", "artikel")
    # Artikel und Ziel widersprechen sich fuer dieselbe Zahl: unklar.
    assert belegstufe("24", "week 24", "followed for 24 months") == ("", "unklar")
    # Keine Artikel-Evidenz: nur aus dem Ziel, also zirkulaer.
    assert belegstufe("24", "week 24", "no time given") == ("week 24", "ziel")
    # Mehrere Einheiten fuer dieselbe Zahl: unklar.
    assert belegstufe("24", "week 24", "at 24 weeks and at 24 months") == ("", "unklar")
    assert belegstufe("0", "baseline", "") == ("baseline", "ziel")
    assert belegstufe("0", "week 24", "") == ("", "unklar")
    assert belegstufe("", "week 24", "") == ("", "leer")


def test_dezimalzahlen_belegen_keine_ganzzahl() -> None:
    from extended_benchmark.evaluate_fallback import einheiten_im_artikel

    assert einheiten_im_artikel(12, "dose 12.5 mg at week 3") == set()
    assert einheiten_im_artikel(24, "Weeks (0, 12, 24) of treatment") == {"week"}
    assert einheiten_im_artikel(24, "0, 12, 24 weeks of follow-up") == {"week"}


def test_rueckfallintervall_klammert_unklare_zellen() -> None:
    from extended_benchmark.evaluate_fallback import rueckfall_intervall

    block = rueckfall_intervall({"zieltreu": 60, "rueckfall": 30, "unklar": 10})
    assert block["untere_grenze"] == round(30 / 100, 4)
    assert block["obere_grenze"] == round(40 / 100, 4)
    leer = rueckfall_intervall({})
    assert leer["untere_grenze"] is None


def test_armklassen_trennen_modell_und_gold() -> None:
    from extended_benchmark.evaluate_fallback import arm_klasse, zahlen_in_zeile

    cells = [
        {"arm": "intervention", "timepoint": "24"},
        {"arm": "comparator", "timepoint": "0"},
    ]
    assert arm_klasse(cells, [11.97, 13.72], "", "week 24") == "arm_gemischt_modell"
    assert (
        arm_klasse(cells, [11.97, 13.72], "0   7.62   11.97 +- 4.00   24   13.72 +- 4.53", "week 24")
        == "arm_gemischt_gold_kandidat"
    )
    assert zahlen_in_zeile([11.97, 13.72], "nur 11.97 hier\n13.72 dort") is False
    gleich = [{"arm": "intervention", "timepoint": "24"}, {"arm": "comparator", "timepoint": "24"}]
    assert arm_klasse(gleich, [1.0, 2.0], "", "week 24") == "arm_konsistent"


def test_zellen_ohne_zeitpunkt_sind_eigene_klasse() -> None:
    assert klassifiziere("post-test", "post-test") == "zieltreu"
    assert klassifiziere("post-test", "") == "ohne_zeitpunkt"
    assert klassifiziere("post-test", "follow up after 4 months") == "rueckfall"
    assert klassifiziere("", "post-test") == "ohne_ziel"
    assert klassifiziere("", "") == "ohne_ziel"
