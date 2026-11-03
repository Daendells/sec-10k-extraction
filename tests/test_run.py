import json

from extraction.run import score_filing


def test_score_filing_scales_verifies_and_handles_missing_answers():
    filing = {"ticker": "AAPL", "truth": {"revenue": 416161e6, "diluted_eps": 7.46, "cash": 35934e6}}
    excerpts = ["Total net sales | $ | 416,161 | $ | 391,035", "Diluted | $ | 7.46 | $ | 6.08"]
    reply = {"revenue": {"value": "416,161", "scale": "millions", "evidence": "Total net sales | $ | 416,161"},
             "diluted_eps": {"value": 7.46, "scale": "millions", "evidence": "Diluted | $ | 7.46"},
             "cash": {"value": None, "scale": None, "evidence": None}}
    rows = {r["field"]: r for r in score_filing(filing, {"reply": json.dumps(reply)}, excerpts)}
    assert rows["revenue"]["correct"] and rows["revenue"]["verified"]
    assert rows["diluted_eps"]["correct"]                     # EPS is not scaled even if the model says millions
    assert rows["cash"]["pred"] is None and not rows["cash"]["correct"] and not rows["cash"]["in_excerpts"]


def test_score_filing_survives_a_reply_that_is_not_json():
    filing = {"ticker": "X", "truth": {"revenue": 1e9}}
    rows = score_filing(filing, {"reply": "sorry"}, ["nothing"])
    assert rows[0]["pred"] is None
