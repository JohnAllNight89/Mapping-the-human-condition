"""
Reproduces the Master Outline's own worked example -- Johnathon Anthony
Long, 23 June 1989, 21:55 EDT, Atlanta, GA -- and checks the computed
Blueprint against every number the source document states for that
profile. Two figures (Design Sun gate and the GK-3 programming-partner
examples) are documented as known, explained divergences: the design
moment math is independently verified as internally self-consistent
(Newton-Raphson residual, Rule V-3 date-window, Profile *line* match),
and the discrepancy traces to the outline's own hand-typed example
reusing the Personality Earth value -- see README.md "Known findings".
"""
from datetime import date

import pytest

from blueprint_calculator.pipeline import run_pipeline

PROFILE_KWARGS = dict(
    name="Johnathon Anthony Long", birth_date="1989-06-23", birth_time="21:55",
    birth_place="Atlanta", today=date(2026, 7, 26),
)


@pytest.fixture(scope="module")
def report():
    return run_pipeline(**PROFILE_KWARGS)


def test_numerology_matches_doc_exactly(report):
    n = report.numerology
    assert n["life_path"] == 11
    assert n["attitude"] == 11  # June (6) + day 23 (2+3=5) = 11 master number, not reduced
    assert n["birthday"] == 5
    assert n["generation"] == 9
    assert n["expression"] == 7
    assert n["soul_urge"] == 33
    assert n["personality"] == 1
    assert n["maturity"] == 9
    assert n["balance"] == 5
    assert n["personal_year"] == 3  # doc's own example, computed "as of" July 2026


def test_v13_name_decomposition_identity(report):
    n = report.numerology
    assert n["expression_raw"] == n["soul_urge_raw"] + n["personality_raw"]
    assert n["expression_raw"] == 97
    assert n["soul_urge_raw"] == 33
    assert n["personality_raw"] == 64


def test_western_headline_signs_match_doc(report):
    w = report.western
    assert w["sun_sign"] == "Cancer"
    assert w["moon_sign"] == "Pisces"
    assert w["ascendant"] == "Capricorn"


def test_ayanamsa_matches_doc(report):
    # doc: 23*42'36" (~23.71 deg)
    assert report.vedic  # sanity that vedic ran
    ayanamsa = report.ledger.value("V-1")
    assert ayanamsa == pytest.approx(23.710105, abs=1e-4)


def test_vedic_moon_matches_doc(report):
    v = report.vedic
    assert v["moon_rashi"] == "Kumbha (Aquarius)"
    assert v["moon_nakshatra"] == "Shatabhisha"
    assert v["moon_nakshatra_lord"] == "Rahu"
    assert v["nakshatras"]["Moon"]["pada"] == 1


def test_vedic_lagna_matches_doc(report):
    v = report.vedic
    assert v["lagna"] == "Dhanu (Sagittarius)"
    assert v["lagna_lord"] == "Jupiter"


def test_human_design_headline_matches_doc(report):
    h = report.human_design
    assert h["type"] == "Projector"
    assert h["authority"] == "Splenic"
    assert h["definition"] == "Split"
    assert h["profile"] == "5/1"  # personality Sun line 5, design Sun line 1


def test_personality_sun_gate_matches_doc(report):
    # doc: "Personality Sun Gate/Line: 15.5"
    assert report.human_design["personality_activations"]["Sun"]["notation"] == "15.5"


def test_gene_keys_lifes_work_and_evolution_match_doc(report):
    g = report.gene_keys
    assert g["lifes_work"] == "15.5"
    assert g["evolution"] == "10.5"


def test_all_validation_rules_pass(report):
    # doc: "all 15 rules PASS"
    assert len(report.validations) == 15
    failed = [v.rule_id for v in report.validations if not v.passed]
    assert failed == []


def test_design_moment_is_self_consistent_even_though_doc_example_differs(report):
    """Known, documented divergence -- see README.md.

    The doc's hand-typed example states Design Sun Gate/Line = 10.5, but
    that number is provably the Personality *Earth* activation (10.5),
    not a real Design-moment Sun position. This test asserts our
    independently-verified value and the internal consistency that
    proves it: the Design Sun *line* still matches the doc's stated
    Profile (5/1), and the solver's day-count lands inside the
    outline's own Rule V-3 tolerance (85-92 days).
    """
    h = report.human_design
    assert h["design_activations"]["Sun"]["line"] == 1  # matches doc's Profile "5/1"
    assert h["personality_activations"]["Earth"]["notation"] == "10.5"  # the value the doc's example actually shows
    diff_days = report.julian_day - report.ledger.value("P3-9")
    assert 85.0 <= diff_days <= 92.0


def test_trace_returns_full_ancestry_to_raw_inputs(report):
    chain = report.ledger.trace("HD-10")
    ids = [dp.id for dp in chain]
    assert ids[0] == "P1"
    assert ids[-1] == "HD-10"
    assert "P3-3" in ids  # Julian Day
    assert "HD-7" in ids  # Defined Channels
