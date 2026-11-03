"""Score extracted values against the XBRL answer key."""

from __future__ import annotations

TOLERANCE = 0.005  # 0.5%: rounding in the text (e.g. EPS to two decimals) stays correct


def is_correct(pred: float | None, truth: float, tol: float = TOLERANCE) -> bool:
    return pred is not None and abs(pred - truth) <= tol * abs(truth)


def _scale_error(pred: float | None, truth: float) -> bool:
    if pred is None or truth == 0 or is_correct(pred, truth):
        return False
    ratio = abs(pred / truth)
    return any(abs(ratio / f - 1) <= TOLERANCE for f in (1e-6, 1e-3, 1e3, 1e6))


def _stats(rows: list[dict]) -> dict:
    n = len(rows)
    correct = [is_correct(r["pred"], r["truth"]) for r in rows]
    return {
        "n": n,
        "accuracy": round(sum(correct) / n, 4) if n else None,
        "coverage": round(sum(r["pred"] is not None for r in rows) / n, 4) if n else None,
        "scale_errors": sum(_scale_error(r["pred"], r["truth"]) for r in rows),
        "verified_correct": sum(ok and r["verified"] for ok, r in zip(correct, rows)),
        "verified_wrong": sum((not ok) and r["pred"] is not None and r["verified"] for ok, r in zip(correct, rows)),
    }


def summarize(rows: list[dict]) -> dict:
    fields = sorted({r["field"] for r in rows})
    return {"overall": _stats(rows), "by_field": {f: _stats([r for r in rows if r["field"] == f]) for f in fields}}
