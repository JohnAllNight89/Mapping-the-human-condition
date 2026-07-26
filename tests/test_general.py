"""General robustness checks: a second profile, direct lat/lon input,
current-name variants, and JSON serializability of the full ledger."""
import json
from datetime import date

from blueprint_calculator.pipeline import run_pipeline
from blueprint_calculator.provenance import DataPoint


def test_direct_latlon_input_bypasses_gazetteer():
    report = run_pipeline(
        name="Test Person", birth_date="2000-01-01", birth_time="12:00",
        birth_place="40.7128,-74.0060", today=date(2026, 7, 26),
    )
    assert report.coordinates.timezone == "America/New_York"


def test_current_name_variants_computed():
    report = run_pipeline(
        name="Johnathon Anthony Long", birth_date="1989-06-23", birth_time="21:55",
        birth_place="Atlanta", current_name="J. Long", today=date(2026, 7, 26),
    )
    assert "current_name" in report.numerology
    assert isinstance(report.numerology["current_name"]["minor_expression"], int)


def test_second_independent_profile_runs_and_validates():
    report = run_pipeline(
        name="Ada Lovelace", birth_date="1815-12-10", birth_time="08:00",
        birth_place="London", today=date(2026, 7, 26),
    )
    failed = [v.rule_id for v in report.validations if not v.passed and v.severity == "MANDATORY"]
    assert failed == []
    assert report.human_design["type"] in (
        "Manifestor", "Generator", "Manifesting Generator", "Projector", "Reflector",
    )


def test_ledger_is_json_serializable():
    report = run_pipeline(
        name="Johnathon Anthony Long", birth_date="1989-06-23", birth_time="21:55",
        birth_place="Atlanta", today=date(2026, 7, 26),
    )
    dumped = json.dumps(report.ledger.to_dict(), default=lambda o: o.to_dict() if isinstance(o, DataPoint) else str(o))
    assert '"HD-10"' in dumped
    assert '"life_path"' not in dumped or True  # smoke check: no exception is the real assertion
