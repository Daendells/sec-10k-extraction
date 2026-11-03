import pytest

from extraction.llm import parse_json
from extraction.score import is_correct, summarize


def test_parse_json_handles_fences_and_chatter():
    assert parse_json('Here you go:\n```json\n{"revenue": {"value": 1}}\n```') == {"revenue": {"value": 1}}
    with pytest.raises(ValueError):
        parse_json("no json here")


def test_is_correct_within_half_a_percent():
    assert is_correct(416161e6, 416161e6)
    assert is_correct(1004, 1000)
    assert not is_correct(1010, 1000)
    assert not is_correct(None, 1000)


def test_summarize_counts_accuracy_coverage_scale_errors_and_verified():
    rows = [
        {"field": "revenue", "truth": 1000.0, "pred": 1000.0, "verified": True},
        {"field": "revenue", "truth": 1000.0, "pred": 1.0, "verified": True},        # off by 1000x
        {"field": "cash", "truth": 50.0, "pred": None, "verified": False},
        {"field": "cash", "truth": 50.0, "pred": 60.0, "verified": False},
    ]
    s = summarize(rows)
    assert s["overall"] == {"n": 4, "accuracy": 0.25, "coverage": 0.75, "scale_errors": 1, "verified_correct": 1,
                            "verified_wrong": 1}
    assert s["by_field"]["revenue"]["accuracy"] == 0.5
